import os
from pathlib import Path
from typing import List, Optional

import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

BASE = Path(__file__).parent

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

ALIASES = {"num_workers": "workers"}
TRUTHY = {"true", "1", "yes", "on"}


def norm_key(k: str) -> str:
    k = k.strip().lower()
    return ALIASES.get(k, k)


def load_yaml() -> dict:
    env = os.environ.get("APP_ENV", "development")
    p = BASE / f"config.{env}.yaml"
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text()) or {}
    return {norm_key(str(k)): v for k, v in data.items()}


def load_dotenv() -> dict:
    out = {}
    p = BASE / ".env"
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        if k.upper().startswith("APP_"):
            k = k[4:]
        v = v.strip().strip('"').strip("'")
        out[norm_key(k)] = v
    return out


def load_os_env() -> dict:
    out = {}
    for k, v in os.environ.items():
        if k.upper().startswith("APP_") and k.upper() != "APP_ENV":
            out[norm_key(k[4:])] = v
    return out


def coerce(key: str, value):
    if key in ("port", "workers"):
        return int(str(value).strip())
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in TRUTHY
    return str(value)


@app.get("/effective-config")
def effective_config(set: Optional[List[str]] = Query(default=None)):
    merged = dict(DEFAULTS)
    merged.update(load_yaml())
    merged.update(load_dotenv())
    merged.update(load_os_env())

    for item in set or []:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        merged[norm_key(k)] = v.strip()

    try:
        result = {k: coerce(k, v) for k, v in merged.items()}
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    result["api_key"] = "****"
    return result