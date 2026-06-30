"""GitHub profile adapter.

Deterministic by default: reads a recorded fixture (``github.json``) so runs are
reproducible and offline. With ``live=True`` it calls the public GitHub REST API and
refreshes the cache. Network/parse failures degrade to the fixture (or empty) — never a
crash.

Fixture / response shape (a trimmed subset of the real API):
    {"user": {"login","name","bio","location","blog","html_url"},
     "languages": ["Python", "JavaScript", ...]}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..models import Method
from .base import ExtractResult, SourceAdapter

_API = "https://api.github.com"


class GithubAdapter(SourceAdapter):
    source = "github"

    def __init__(self, live: bool = False, cache_dir: Optional[Path] = None):
        self.live = live
        self.cache_dir = Path(cache_dir) if cache_dir else None

    def extract(self, path: Path) -> ExtractResult:
        result = ExtractResult()
        path = Path(path)
        blob: Optional[dict] = None

        if path.suffix == ".json":
            blob = self._load_fixture(path, result)
            login = (blob or {}).get("user", {}).get("login")
            if self.live and login:
                fetched = self._fetch_live(login, result)
                if fetched:
                    blob = fetched
                    self._write_cache(login, fetched)
        else:
            login = self._read_login(path)
            if not login:
                result.warnings.append(f"{self.source}: no username/url in {path}")
                return result
            if self.live:
                blob = self._fetch_live(login, result) or self._load_cache(login, result)
            else:
                blob = self._load_cache(login, result)

        if not blob:
            return result
        self._emit(blob, result)
        return result

    # --- input resolution ------------------------------------------------------------ #
    def _read_login(self, path: Path) -> Optional[str]:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            return None
        text = text.splitlines()[0].strip().rstrip("/")
        return text.split("/")[-1] if "/" in text else text

    def _load_fixture(self, path: Path, result: ExtractResult) -> Optional[dict]:
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, json.JSONDecodeError) as exc:
            result.warnings.append(f"{self.source}: bad fixture {path} ({exc})")
            return None
        return data if isinstance(data, dict) else None

    def _load_cache(self, login: str, result: ExtractResult) -> Optional[dict]:
        if not self.cache_dir:
            result.warnings.append(f"{self.source}: no cache dir for {login}")
            return None
        cache = self.cache_dir / f"github_{login}.json"
        if not cache.exists():
            result.warnings.append(f"{self.source}: no cached fixture for {login}")
            return None
        return self._load_fixture(cache, result)

    def _write_cache(self, login: str, blob: dict) -> None:
        if not self.cache_dir:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / f"github_{login}.json").write_text(
            json.dumps(blob, indent=2, sort_keys=True), encoding="utf-8"
        )

    # --- live fetch (best-effort) ---------------------------------------------------- #
    def _fetch_live(self, login: str, result: ExtractResult) -> Optional[dict]:
        try:
            import requests

            headers = {"Accept": "application/vnd.github+json"}
            user = requests.get(f"{_API}/users/{login}", headers=headers, timeout=10)
            user.raise_for_status()
            u = user.json()
            repos = requests.get(
                f"{_API}/users/{login}/repos",
                headers=headers, params={"per_page": 100, "sort": "pushed"}, timeout=10,
            )
            repos.raise_for_status()
            languages = sorted({r["language"] for r in repos.json() if r.get("language")})
            return {
                "user": {
                    k: u.get(k) for k in ("login", "name", "bio", "location", "blog", "html_url")
                },
                "languages": languages,
            }
        except Exception as exc:  # noqa: BLE001 - degrade gracefully on any network error
            result.warnings.append(f"{self.source}: live fetch failed for {login} ({exc})")
            return None

    # --- claim emission -------------------------------------------------------------- #
    def _emit(self, blob: dict, result: ExtractResult) -> None:
        user = blob.get("user") or {}
        if user.get("name"):
            result.claims.append(self._claim("full_name", user["name"], Method.API))
        if user.get("bio"):
            result.claims.append(self._claim("headline", user["bio"], Method.API))
        if user.get("html_url"):
            result.claims.append(self._claim("links.github", user["html_url"], Method.API))
        if user.get("blog"):
            result.claims.append(self._claim("links.portfolio", user["blog"], Method.API))

        # Free-text location like "San Francisco, CA, USA" -> parsed (fuzzy).
        loc = (user.get("location") or "").strip()
        if loc:
            parts = [p.strip() for p in loc.split(",") if p.strip()]
            if parts:
                result.claims.append(self._claim("location.city", parts[0], Method.REGEX))
                result.claims.append(self._claim("location.country", parts[-1], Method.REGEX))

        for lang in blob.get("languages") or []:
            if isinstance(lang, str) and lang.strip():
                result.claims.append(self._claim("skills", lang.strip(), Method.API))
