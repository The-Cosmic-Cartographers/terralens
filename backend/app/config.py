import os
from pathlib import Path

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("TERRALENS_CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

# Reported by /health when the data folder has no data_version.txt.
DATA_VERSION_FALLBACK = "unversioned"


def data_dir() -> Path:
    """The data root: ./data by default, ./data/fixtures for SAMPLE data."""
    return Path(os.environ.get("TERRALENS_DATA_DIR", "./data"))
