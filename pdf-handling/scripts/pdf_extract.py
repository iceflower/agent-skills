#!/usr/bin/env python3
"""Wrap pdftoppm/pdftotext workflow into a single command.

Extracts content from PDF files using poppler utilities.
Auto-detects whether to use pdftotext (text-based PDF) or pdftoppm (scanned PDF).
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple


def check_poppler_installed() -> Tuple[bool, str]:
    """Check if poppler utilities are installed."""
    pdftotext = shutil.which("pdftotext")
    pdftoppm = shutil.which("pdftoppm")

    if pdftotext and pdftoppm:
        return True, ""

    system = platform.system().lower()
    if system == "darwin":
        instructions = "brew install poppler"
    elif system == "linux":
        # Detect distro
        distro_info = ""
        try:
            with open("/etc/os-release", "r") as f:
                distro_info = f.read().lower()
        except OSError:
            pass

        if "opensuse" in distro_info or "suse" in distro_info:
            instructions = "sudo zypper install poppler-tools"
        elif "ubuntu" in distro_info or "debian" in distro_info:
            instructions = "sudo apt install poppler-utils"
        elif "fedora" in distro_info or "rhel" in distro_info or "centos" in distro_info:
            instructions = "sudo dnf install poppler-utils"
        elif "arch" in distro_info:
            instructions = "sudo pacman -S poppler"
        else:
            instructions = (
                "Install poppler-utils via your package manager:\n"
                "  Ubuntu/Debian: sudo apt install poppler-utils\n"
                "  openSUSE:      sudo zypper install poppler-tools\n"
                "  Fedora/RHEL:   sudo dnf install poppler-utils\n"
                "  Arch:          sudo pacman -S poppler"
            )
    elif system == "windows":
        instructions = (
            "Install poppler for Windows:\n"
            "  choco install poppler\n"
            "  scoop install poppler\n"
            "Or download from: https://github.com/oschwartz10612/poppler-windows/releases"
        )
    else:
        instructions = "Install poppler utilities for your platform"

    missing = []
    if not pdftotext:
        missing.append("pdftotext")
    if not pdftoppm:
        missing.append("pdftoppm")

    msg = (
        f"Missing poppler utilities: {', '.join(missing)}\n"
        f"Install with:\n  {instructions}"
    )
    return False, msg


def get_page_count(pdf_path: str) -> Optional[int]:
    """Get total page count of a PDF using pdfinfo."""
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        return None

    try:
        result = subprocess.run(
            [pdfinfo, pdf_path],
            capture_output=True, text=True, timeout=30,
        )
        for line in result.stdout.splitlines():
            if line.lower().startswith("pages:"):
                return int(line.split(":", 1)[1].strip())
    except (subprocess.SubprocessError, ValueError):
        pass
    return None


def parse_page_range(pages_str: str, total_pages: Optional[int]) -> Tuple[int, int]:
    """Parse page range string like '1-5', '3', '10-20'."""
    pages_str = pages_str.strip()

    if "-" in pages_str:
        parts = pages_str.split("-", 1)
        first = int(parts[0].strip())
        last = int(parts[1].strip())
    else:
        first = int(pages_str)
        last = first

    if first < 1:
        first = 1
    if total_pages and last > total_pages:
        last = total_pages

    return first, last


def is_text_pdf(pdf_path: str, first_page: int = 1, last_page: int = 1) -> bool:
    """Check if the PDF contains extractable text (not scanned)."""
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return False

    try:
        result = subprocess.run(
            [pdftotext, "-f", str(first_page), "-l", str(last_page), pdf_path, "-"],
            capture_output=True, text=True, timeout=30,
        )
        text = result.stdout.strip()
        # If we get meaningful text (more than just whitespace/control chars),
        # consider it a text-based PDF
        meaningful_chars = sum(1 for c in text if c.isalnum())
        return meaningful_chars > 20
    except subprocess.SubprocessError:
        return False


def extract_text(
    pdf_path: str, output_dir: str, first_page: int, last_page: int
) -> List[str]:
    """Extract text from PDF using pdftotext."""
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        print("Error: pdftotext not found", file=sys.stderr)
        return []

    output_files: List[str] = []
    base_name = Path(pdf_path).stem

    # Extract all pages at once
    output_file = os.path.join(output_dir, f"{base_name}_p{first_page}-{last_page}.txt")

    cmd = [
        pdftotext,
        "-f", str(first_page),
        "-l", str(last_page),
        "-layout",
        pdf_path,
        output_file,
    ]

    print(f"Extracting text: pages {first_page}-{last_page} ...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"Warning: pdftotext returned code {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(f"  {result.stderr.strip()}", file=sys.stderr)
    else:
        if os.path.isfile(output_file) and os.path.getsize(output_file) > 0:
            output_files.append(output_file)
            print(f"  Created: {output_file}")

    return output_files


def extract_images(
    pdf_path: str, output_dir: str, first_page: int, last_page: int, dpi: int = 300
) -> List[str]:
    """Extract pages as PNG images using pdftoppm."""
    pdftoppm_bin = shutil.which("pdftoppm")
    if not pdftoppm_bin:
        print("Error: pdftoppm not found", file=sys.stderr)
        return []

    output_files: List[str] = []
    base_name = Path(pdf_path).stem
    output_prefix = os.path.join(output_dir, base_name)

    cmd = [
        pdftoppm_bin,
        "-png",
        "-r", str(dpi),
        "-f", str(first_page),
        "-l", str(last_page),
        pdf_path,
        output_prefix,
    ]

    print(f"Converting to images: pages {first_page}-{last_page} (DPI: {dpi}) ...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"Warning: pdftoppm returned code {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(f"  {result.stderr.strip()}", file=sys.stderr)

    # Collect generated files
    for fname in sorted(os.listdir(output_dir)):
        full_path = os.path.join(output_dir, fname)
        if fname.startswith(base_name) and fname.endswith(".png"):
            output_files.append(full_path)
            print(f"  Created: {full_path}")

    return output_files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract content from PDF files using poppler utilities.",
        epilog=(
            "Auto-detects whether to use pdftotext (text PDF) or pdftoppm (scanned PDF).\n"
            "Requires poppler to be installed."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "pdf",
        help="Path to the PDF file",
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="Page range to extract (e.g., '1-5', '3', '10-20'). Default: all pages.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: /tmp/pdf_extract_<timestamp>)",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "text", "image"],
        default="auto",
        help="Extraction mode: auto (detect), text (pdftotext), image (pdftoppm). Default: auto.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for image extraction (default: 300)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove output directory after printing file list",
    )

    args = parser.parse_args()

    # Check poppler
    installed, install_msg = check_poppler_installed()
    if not installed:
        print(f"Error: {install_msg}", file=sys.stderr)
        return 1

    # Validate PDF path
    if not os.path.isfile(args.pdf):
        print(f"Error: File not found: {args.pdf}", file=sys.stderr)
        return 1

    # Get page count
    total_pages = get_page_count(args.pdf)
    if total_pages:
        print(f"PDF: {args.pdf} ({total_pages} pages)")
    else:
        print(f"PDF: {args.pdf} (page count unknown)")

    # Parse page range
    if args.pages:
        try:
            first_page, last_page = parse_page_range(args.pages, total_pages)
        except ValueError:
            print(f"Error: Invalid page range: {args.pages}", file=sys.stderr)
            return 1
    else:
        first_page = 1
        last_page = total_pages or 9999

    # Setup output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        timestamp = int(time.time())
        output_dir = os.path.join(tempfile.gettempdir(), f"pdf_extract_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Determine extraction mode
    mode = args.mode
    if mode == "auto":
        print("Detecting PDF type ...")
        if is_text_pdf(args.pdf, first_page, min(first_page + 1, last_page)):
            mode = "text"
            print("  Detected: text-based PDF (using pdftotext)")
        else:
            mode = "image"
            print("  Detected: scanned/image-based PDF (using pdftoppm)")

    # Extract
    output_files: List[str] = []
    if mode == "text":
        output_files = extract_text(args.pdf, output_dir, first_page, last_page)
    elif mode == "image":
        output_files = extract_images(args.pdf, output_dir, first_page, last_page, args.dpi)

    if not output_files:
        print("Warning: No output files were generated", file=sys.stderr)
        return 1

    print(f"\nExtracted {len(output_files)} file(s)")

    # Cleanup if requested
    if args.cleanup:
        print(f"Cleaning up: {output_dir}")
        shutil.rmtree(output_dir, ignore_errors=True)
        print("Cleanup complete")

    return 0


if __name__ == "__main__":
    sys.exit(main())
