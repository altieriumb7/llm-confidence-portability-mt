import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

from utils.parse import coerce_confidence

try:
    import yaml
except Exception:
    yaml = None

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False


def setup_logging(log_path: Path, name: str = "mt") -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    fh = logging.FileHandler(log_path)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    return logger


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _naive_yaml_load(text: str) -> Dict[str, Any]:
    out = {"global": {}, "models": []}
    section = None
    current = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("global:"):
            section = "global"; continue
        if line.startswith("models:"):
            section = "models"; continue
        if section == "global":
            if ":" in line:
                k, v = [x.strip() for x in line.split(":", 1)]
                out["global"][k] = _coerce(v)
        elif section == "models":
            if line.strip().startswith("-"):
                current = {}
                out["models"].append(current)
                kv = line.strip()[1:].strip()
                if kv and ":" in kv:
                    k, v = [x.strip() for x in kv.split(":", 1)]
                    current[k] = _coerce(v)
            elif current is not None and ":" in line:
                k, v = [x.strip() for x in line.split(":", 1)]
                current[k] = _coerce(v)
    return out

def _coerce(v: str):
    v = v.strip().strip("\"'")
    if v.lower() in {"true", "false"}:
        return v.lower() == "true"
    try:
        if "." in v:
            return float(v)
        return int(v)
    except Exception:
        return v

def load_config(path: str) -> Dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    return _naive_yaml_load(text)


def load_env() -> None:
    load_dotenv(override=False)


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_confidence(raw: Any) -> Optional[float]:
    if isinstance(raw, dict):
        raw = raw.get("confidence")
    return coerce_confidence(raw)


def usage_to_tokens(usage: Optional[Dict[str, Any]]) -> Dict[str, Optional[int]]:
    if not usage:
        return {"input_tokens": None, "output_tokens": None}
    in_tok = usage.get("input_tokens") or usage.get("prompt_tokens")
    out_tok = usage.get("output_tokens") or usage.get("completion_tokens")
    try:
        in_tok = int(in_tok) if in_tok is not None else None
    except Exception:
        in_tok = None
    try:
        out_tok = int(out_tok) if out_tok is not None else None
    except Exception:
        out_tok = None
    return {"input_tokens": in_tok, "output_tokens": out_tok}


def retry_with_backoff(func: Callable[[], Any], max_retries: int, logger: logging.Logger, label: str) -> Any:
    delay = 1.0
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as exc:
            msg = str(exc)
            lower = msg.lower()
            non_retryable_quota = (
                ("resource_exhausted" in lower and "quota exceeded" in lower and "limit: 0" in lower)
                or ("insufficient_quota" in lower)
            )
            if non_retryable_quota:
                raise
            retryable = any(code in msg for code in ["429", "500", "502", "503", "504", "529", "timeout"]) or ("overloaded" in msg.lower())
            if attempt >= max_retries or not retryable:
                raise
            logger.warning("%s failed (%s). retry %s/%s in %.1fs", label, msg, attempt + 1, max_retries, delay)
            time.sleep(delay)
            delay = min(delay * 2, 20)


def seeded_sample(items: list, n: int, seed: int) -> list:
    n = min(n, len(items))
    rnd = random.Random(seed)
    idxs = list(range(len(items)))
    rnd.shuffle(idxs)
    return [items[i] for i in idxs[:n]]
