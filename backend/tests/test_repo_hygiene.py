"""Nothing secret and nothing raw is committed; the deployed snapshot is never SAMPLE."""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        pytest.skip("not a git checkout")
    return [ROOT / line for line in result.stdout.splitlines() if (ROOT / line).is_file()]


def test_env_example_has_names_only():
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            name, _, value = line.partition("=")
            assert re.fullmatch(r"[A-Z][A-Z0-9_]*", name), line
            # Allowed values are plain local settings, never credentials.
            assert not re.search(r"(key|token|secret|password)", name, re.IGNORECASE), line
            assert not value or value.startswith(("http://localhost", "./")), line


def test_no_credential_files_or_patterns_are_tracked():
    bad_names = {".env", ".netrc", "id_rsa", "id_ed25519"}
    pattern = re.compile(
        r"(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}"
        r"|xox[bp]-[0-9A-Za-z-]{10,}|machine\s+urs\.earthdata\.nasa\.gov)"
    )
    for path in tracked_files():
        assert path.name not in bad_names and path.suffix != ".pem", path
        if path.suffix in {".py", ".md", ".json", ".yml", ".yaml", ".toml", ".txt", ".ts", ".tsx"}:
            if path.name == "test_repo_hygiene.py":
                continue
            assert not pattern.search(path.read_text(encoding="utf-8", errors="ignore")), path


def test_no_raw_nasa_files_are_tracked():
    raw_suffixes = {".nc", ".nc4", ".hdf", ".hdf5", ".h5", ".he5", ".grib", ".tif", ".zip"}
    for path in tracked_files():
        relative = path.relative_to(ROOT)
        assert path.suffix.lower() not in raw_suffixes, relative
        if relative.parts[:2] == ("data", "raw"):
            assert relative.name == ".gitkeep", relative


def test_a_committed_snapshot_is_never_sample_data():
    folder = ROOT / "frontend" / "nasa-earth-trends" / "public" / "data"
    if not (folder / "health.json").is_file():
        pytest.skip("no snapshot is committed")
    from app.verify_snapshot import verify

    assert verify(folder) == []
