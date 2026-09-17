"""BurpNake Deduplication + Smart Filter
Aynı statik asset'leri (logo, favicon, .js, .css vb.) filtreler.
Burp her tıklamada bunları tekrar gönderir ve DB'yi şişirir.
"""
from __future__ import annotations
import re
import hashlib
from threading import Lock
from urllib.parse import urlparse

# Statik asset uzantıları — bunlar hiçbir zaman ilginç değil
STATIC_EXTENSIONS = {
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".otf", ".map", ".mp4", ".mp3",
    ".webp", ".avif", ".pdf", ".zip",
}

# İçerik tiplerine göre filtrele
BORING_CONTENT_TYPES = {
    "text/css", "application/javascript", "image/", "font/",
    "audio/", "video/",
}

# Hash seti — son 10.000 isteği hafızada tut (daha eski olanlar zaten DB'de)
MAX_HASH_CACHE = 10_000


class DedupFilter:
    """HTTP exchange'leri için deduplication ve akıllı filtreleme."""

    def __init__(self):
        self._seen_hashes: set[str] = set()
        self._hash_order: list[str] = []
        self._lock = Lock()

    def should_skip(self, exchange_data: dict) -> tuple[bool, str]:
        """
        True dönerse exchange skip edilmeli.
        Returns: (should_skip: bool, reason: str)
        """
        url = exchange_data.get("url", "") or exchange_data.get("path", "")
        method = exchange_data.get("method", "GET").upper()
        status = exchange_data.get("status_code", 0) or 0

        # 1. Statik uzantı kontrolü
        path = urlparse(url).path.lower()
        ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
        if ext in STATIC_EXTENSIONS:
            return True, f"static_asset:{ext}"

        # 2. OPTIONS metodlarını atla (genellikle ilginç değil)
        # Only skip OPTIONS, not HEAD (HEAD can reveal info)
        if method in ("OPTIONS",):
            return True, f"boring_method:{method}"

        # REMOVED: 3xx redirects are needed for open redirect detection
        # if 300 <= status < 400:
        #     return True, f"redirect:{status}"

        # 4. İçerik tipi kontrolü (response headers'dan)
        req_headers = exchange_data.get("request_headers", {}) or {}
        if isinstance(req_headers, str):
            import json
            try:
                req_headers = json.loads(req_headers)
            except Exception:
                req_headers = {}
        
        content_type = ""
        if isinstance(req_headers, dict):
            content_type = req_headers.get("Accept", "").lower()
        
        for boring in BORING_CONTENT_TYPES:
            if boring in content_type:
                return True, f"boring_content_type:{boring}"

        # 5. Exact duplicate kontrolü (aynı method+path+body hash)
        h = self._compute_hash(exchange_data)
        with self._lock:
            if h in self._seen_hashes:
                return True, "exact_duplicate"
            # Cache'e ekle, fazlasını temizle
            self._seen_hashes.add(h)
            self._hash_order.append(h)
            if len(self._hash_order) > MAX_HASH_CACHE:
                oldest = self._hash_order.pop(0)
                self._seen_hashes.discard(oldest)

        return False, ""

    def _compute_hash(self, data: dict) -> str:
        """Method + path + request body ilk 500 karakterinden hash üretir."""
        method = data.get("method", "GET")
        path = data.get("path", "") or urlparse(data.get("url", "")).path
        # Body'nin ilk kısmı yeterli (tam hash çok pahalı)
        body_prefix = (data.get("request_b64", "") or "")[:100]
        key = f"{method}:{path}:{body_prefix}"
        return hashlib.md5(key.encode()).hexdigest()

    def reset(self):
        with self._lock:
            self._seen_hashes.clear()
            self._hash_order.clear()


# Singleton
dedup_filter = DedupFilter()
