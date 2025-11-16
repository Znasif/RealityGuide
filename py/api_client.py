import argparse
import base64
import json
from pathlib import Path
from typing import Any, Optional
from urllib import error, request

BASE64_PLACEHOLDER = "<omitted base64 image>"


def main() -> None:
    parser = argparse.ArgumentParser(description="Interact with the RealityGuide API.")
    parser.add_argument("image_path", type=Path, help="Path to the image to upload.")
    parser.add_argument(
        "--goal-id",
        type=str,
        default=None,
        help="Existing goal id to update. If omitted, a new goal is created.",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://127.0.0.1:8000",
        help="Base URL for the API server.",
    )
    args = parser.parse_args()

    payload = {"image_base64": _encode_image(args.image_path)}
    response = _send_request(
        base_url=args.base_url,
        goal_id=args.goal_id,
        payload=payload,
    )
    redacted = _redact_base64_images(response)
    print(json.dumps(redacted, indent=2))


def _encode_image(image_path: Path) -> str:
    data = Path(image_path).read_bytes()
    return base64.b64encode(data).decode("ascii")


def _send_request(
    base_url: str, goal_id: Optional[str], payload: dict[str, str]
) -> Any:
    body = json.dumps(payload).encode("utf-8")
    base = base_url.rstrip("/")
    if goal_id:
        url = f"{base}/goals/{goal_id}"
        method = "PUT"
    else:
        url = f"{base}/goals"
        method = "POST"

    req = request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method=method
    )
    try:
        with request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"Request failed with status {exc.code}: {detail}") from exc


def _redact_base64_images(data: Any) -> Any:
    if isinstance(data, dict):
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            if _should_redact_key(key, value):
                redacted[key] = BASE64_PLACEHOLDER
            else:
                redacted[key] = _redact_base64_images(value)
        return redacted
    if isinstance(data, list):
        return [_redact_base64_images(item) for item in data]
    return data


def _should_redact_key(key: Any, value: Any) -> bool:
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    if "image" not in lowered:
        return False
    return "base64" in lowered


if __name__ == "__main__":
    main()
