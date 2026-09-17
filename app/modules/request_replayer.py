"""Request Replayer - Replay and modify HTTP requests."""

from __future__ import annotations
import httpx
from app.models.http_exchange import HttpExchange, HttpRequest, HttpResponse, HttpHeader


class RequestReplayer:
    """Replay HTTP requests with modifications for testing."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=False,
                verify=False,
            )
        return self._client

    async def replay(
        self,
        exchange: HttpExchange,
        modifications: dict | None = None,
    ) -> HttpExchange:
        """
        Replay an HTTP exchange, optionally with modifications.
        
        modifications can include:
        - headers: dict of header name -> value to add/replace
        - params: dict of query param name -> value to add/replace  
        - body: new request body string
        - method: override HTTP method
        - path: override request path
        """
        mods = modifications or {}
        req = exchange.request
        client = await self._get_client()

        # Build URL
        url = f"{req.protocol}://{req.host}"
        if req.port and req.port not in (80, 443):
            url += f":{req.port}"
        url += mods.get("path", req.path)

        # Build headers
        headers = {h.name: h.value for h in req.headers}
        headers.update(mods.get("headers", {}))
        headers.pop("Host", None)  # httpx handles this
        headers.pop("Content-Length", None)

        # Build body
        body = mods.get("body", req.body)
        method = mods.get("method", req.method)

        try:
            resp = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=body.encode() if body else None,
            )

            response = HttpResponse(
                status_code=resp.status_code,
                status_text=resp.reason_phrase or "",
                headers=[
                    HttpHeader(name=k, value=v)
                    for k, v in resp.headers.items()
                ],
                body=resp.text,
                content_type=resp.headers.get("content-type", ""),
                content_length=len(resp.content),
            )

            return HttpExchange(
                id=exchange.id,
                request=exchange.request,
                response=response,
                source="replay",
                notes=f"Replayed with mods: {list(mods.keys())}",
            )
        except Exception as e:
            return HttpExchange(
                id=exchange.id,
                request=exchange.request,
                response=HttpResponse(status_code=0, status_text=str(e)),
                source="replay_error",
                notes=str(e),
            )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


request_replayer = RequestReplayer()
