#!/usr/bin/env python3
"""Simple CLI to run an image through the GLM-OCR API and print markdown."""

import argparse
import base64
import mimetypes
import sys
from pathlib import Path

import requests

DEFAULT_URL = "http://localhost:5002/glmocr/parse"


def ocr(image_path: str, api_url: str = DEFAULT_URL) -> str:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {image_path}")

    mime, _ = mimetypes.guess_type(str(path))
    if mime is None:
        mime = "application/octet-stream"

    data = base64.b64encode(path.read_bytes()).decode()
    data_uri = f"data:{mime};base64,{data}"

    resp = requests.post(
        api_url,
        json={"images": [data_uri]},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json().get("markdown_result", "")


def main():
    parser = argparse.ArgumentParser(description="OCR an image via GLM-OCR API")
    parser.add_argument("image", help="Path to an image file (jpg, png, etc.)")
    parser.add_argument("--api-url", default=DEFAULT_URL, help="GLM-OCR API URL")
    args = parser.parse_args()

    try:
        md = ocr(args.image, args.api_url)
    except requests.HTTPError as e:
        print(f"API error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print(md)


if __name__ == "__main__":
    main()
