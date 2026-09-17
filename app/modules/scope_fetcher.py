"""
HackerOne & Bugcrowd public API'leri uzerinden program scope'unu otomatik ceker.
API key gerekmez - sadece public program handle (slug) yeter.
"""
import httpx
import json
from app.modules.database import save_program

H1_GRAPHQL = "https://hackerone.com/graphql"

H1_QUERY = """
query ProgramScope($handle: String!) {
  team(handle: $handle) {
    name
    structured_scope_versions(current: true) {
      max_updated_at
    }
    in_scope_assets: structured_scopes(
      archived: false
      eligible_for_submission: true
    ) {
      edges {
        node {
          asset_type
          asset_identifier
          instruction
          max_severity
        }
      }
    }
    out_of_scope_assets: structured_scopes(
      archived: false
      eligible_for_submission: false
    ) {
      edges {
        node {
          asset_type
          asset_identifier
        }
      }
    }
  }
}
"""


async def fetch_hackerone_scope(handle: str) -> dict:
    """
    HackerOne public GraphQL API'sinden program scope'unu ceker.
    handle: 'tesla', 'shopify', 'github' gibi program slug.
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 BurpNake/1.0",
    }
    payload = {"query": H1_QUERY, "variables": {"handle": handle}}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(H1_GRAPHQL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    team = data.get("data", {}).get("team")
    if not team:
        raise ValueError(f"Program bulunamadi: {handle}")

    in_scope = []
    out_scope = []

    for edge in team.get("in_scope_assets", {}).get("edges", []):
        node = edge["node"]
        in_scope.append({
            "asset": node["asset_identifier"],
            "type": node["asset_type"],
            "max_severity": node.get("max_severity", ""),
        })

    for edge in team.get("out_of_scope_assets", {}).get("edges", []):
        node = edge["node"]
        out_scope.append({
            "asset": node["asset_identifier"],
            "type": node["asset_type"],
        })

    scope_data = {
        "include": [s["asset"] for s in in_scope if s["type"] in ("URL", "WILDCARD", "DOMAIN")],
        "exclude": [s["asset"] for s in out_scope if s["type"] in ("URL", "WILDCARD", "DOMAIN")],
        "all_in_scope": in_scope,
        "all_out_scope": out_scope,
    }

    # Veritabanina kaydet
    pid = save_program({
        "name": team.get("name", handle),
        "platform": "hackerone",
        "scope": scope_data,
    })

    return {
        "program_id": pid,
        "name": team.get("name", handle),
        "scope": scope_data,
    }


def is_in_scope(url: str, include_list: list, exclude_list: list) -> bool:
    """Bir URL'nin scope icerisinde olup olmadigini kontrol eder."""
    import fnmatch
    from urllib.parse import urlparse

    try:
        host = urlparse(url).netloc or url
    except Exception:
        host = url

    # Once excluded mi bak
    for pattern in exclude_list:
        pattern = pattern.replace("https://", "").replace("http://", "").split("/")[0]
        if fnmatch.fnmatch(host, pattern):
            return False

    # Sonra included mi bak
    for pattern in include_list:
        pattern = pattern.replace("https://", "").replace("http://", "").split("/")[0]
        if fnmatch.fnmatch(host, pattern):
            return True

    return False
