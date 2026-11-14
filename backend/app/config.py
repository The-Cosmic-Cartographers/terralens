import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("TERRALENS_DATA_DIR", "./data"))

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("TERRALENS_CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# Replaced by the export step once real processed data exists.
DATA_VERSION = "unversioned"
