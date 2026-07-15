"""Guard: the package's runtime __version__ must equal its installed metadata
version. A live audit caught 0.8.0 shipping with __version__ = "0.7.0", so the
SDK reported itself as 0.7.0 in its User-Agent on every request. The sibling MCP
package has this guard; the SDK did not."""

from __future__ import annotations

import flopsindex


def test_runtime_version_matches_installed_metadata():
    try:
        from importlib.metadata import version, PackageNotFoundError
    except ImportError:  # pragma: no cover
        from importlib_metadata import version, PackageNotFoundError  # type: ignore

    try:
        meta = version("flopsindex")
    except PackageNotFoundError:
        # not installed (running from source tree) — fall back to pyproject
        import pathlib, re
        pp = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
        meta = re.search(r'^version\s*=\s*"([^"]+)"', pp.read_text(encoding="utf-8"), re.M).group(1)

    assert flopsindex.__version__ == meta, (
        f"flopsindex.__version__ ({flopsindex.__version__!r}) != packaged "
        f"version ({meta!r}); the User-Agent would report the wrong version"
    )
