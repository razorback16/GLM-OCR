#!/usr/bin/env python3
"""CLI to run an image/PDF through the GLM-OCR API and save markdown with images."""

import argparse
import base64
import mimetypes
import sys
from pathlib import Path

import requests
from PIL import Image

from glmocr.utils.markdown_utils import extract_image_refs
from glmocr.utils.image_utils import crop_image_region, pdf_to_images_pil

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


def load_source_pages(path: Path) -> list[Image.Image]:
    """Load pages from the source file for image cropping."""
    if path.suffix.lower() == ".pdf":
        return pdf_to_images_pil(str(path), dpi=200, max_width_or_height=3500)
    img = Image.open(path)
    return [img.convert("RGB") if img.mode != "RGB" else img]


def crop_and_save_images(
    markdown: str, source_path: Path, output_dir: Path
) -> str:
    """Extract image refs from markdown, crop them, and replace tags."""
    image_refs = extract_image_refs(markdown)
    if not image_refs:
        return markdown

    pages = load_source_pages(source_path)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    for idx, (page_idx, bbox, original_tag) in enumerate(image_refs):
        if page_idx < 0 or page_idx >= len(pages):
            print(
                f"Warning: page {page_idx} out of range, skipping",
                file=sys.stderr,
            )
            continue
        try:
            cropped = crop_image_region(pages[page_idx], bbox)
            fname = f"page{page_idx}_{idx}.jpg"
            cropped.save(images_dir / fname, quality=95)
            markdown = markdown.replace(
                original_tag, f"![Image {page_idx}-{idx}](images/{fname})", 1
            )
        except Exception as exc:
            print(f"Warning: failed to crop image (page={page_idx}): {exc}", file=sys.stderr)

    return markdown


def main():
    parser = argparse.ArgumentParser(
        description="OCR an image/PDF via GLM-OCR API and save markdown with images."
    )
    parser.add_argument("input", help="Path to an image or PDF file")
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output directory (default: <input_stem>/)",
    )
    parser.add_argument("--api-url", default=DEFAULT_URL, help="GLM-OCR API URL")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output) if args.output else input_path.parent / input_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"Processing {input_path.name}...", flush=True)
        markdown = ocr(str(input_path), args.api_url)
    except requests.HTTPError as e:
        print(f"API error: {e}", file=sys.stderr)
        sys.exit(1)

    markdown = crop_and_save_images(markdown, input_path, output_dir)

    output_path = output_dir / (input_path.stem + ".md")
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
