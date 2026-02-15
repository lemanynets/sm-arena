import base64
import hashlib
import json
from typing import Any, Dict

def b64encode_json(obj: Dict[str, Any]) -> str:
    raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")

def b64decode_json(data_b64: str) -> Dict[str, Any]:
    raw = base64.b64decode(data_b64)
    return json.loads(raw.decode("utf-8"))

def liqpay_signature(private_key: str, data_b64: str) -> str:
    s = (private_key + data_b64 + private_key).encode("utf-8")
    digest = hashlib.sha1(s).digest()
    return base64.b64encode(digest).decode("ascii")

def verify_callback(private_key: str, data_b64: str, signature: str) -> bool:
    return liqpay_signature(private_key, data_b64) == signature
