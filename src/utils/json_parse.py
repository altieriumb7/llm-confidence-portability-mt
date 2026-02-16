# Backward-compatible shim. Prefer utils.parse.
from utils.parse import extract_first_json_object, parse_json_field

__all__ = ["extract_first_json_object", "parse_json_field"]
