"""QR code generator tool.

Generates a QR code image for the audience Q&A URL.

Usage:
    python tools/generate_qr.py --url https://your-app.com/static/ask.html --output frontend/qr_code.png
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")


def generate_qr(url: str, output_path: str, size: int = 10):
    """Generate a QR code image.

    Args:
        url: The URL to encode.
        output_path: Path to save the PNG image.
        size: Box size for the QR code (default 10).
    """
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="white", back_color="transparent")

        # Save with transparent background if possible
        try:
            img = qr.make_image(fill_color="white", back_color=(15, 12, 41))
        except Exception:
            pass

        img.save(output_path)
        print(f"QR code saved to: {output_path}")
        print(f"URL encoded: {url}")

    except ImportError:
        print("Error: qrcode package not installed. Run: pip install qrcode[pil]")
        sys.exit(1)


def main():
    default_url = os.getenv("PRESENTATION_URL", "http://localhost:8000")
    qa_url = f"{default_url}/static/ask.html"

    parser = argparse.ArgumentParser(description="Generate QR code for audience Q&A")
    parser.add_argument("--url", default=qa_url, help=f"URL to encode (default: {qa_url})")
    parser.add_argument("--output", default="frontend/qr_code.png", help="Output PNG path")
    parser.add_argument("--size", type=int, default=10, help="QR box size")
    args = parser.parse_args()

    output_path = str(project_root / args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    generate_qr(args.url, output_path, args.size)


if __name__ == "__main__":
    main()
