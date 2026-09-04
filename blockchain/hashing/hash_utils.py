import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Union

def canonical_serialize(data: Dict[str, Any]) -> bytes:
    """Sorts keys and standardizes spacing for consistent cryptographic hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

def compute_sha256(content: Union[str, bytes]) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()

def hash_fir_json(file_path: Union[str, Path]) -> Dict[str, str]:
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    digest = compute_sha256(canonical_serialize(data))
    fir_no = data.get("fir_no") or path.stem

    return {
        "fir_no": fir_no,
        "source_file": path.name,
        "data_hash": digest
    }