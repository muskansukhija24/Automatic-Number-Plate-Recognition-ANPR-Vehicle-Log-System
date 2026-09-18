#!/usr/bin/env python3
"""
Automatic Number Plate Recognition (ANPR) & Vehicle Log System
Main Entry Point and Unified Command-Line Interface (CLI).

Subcommands:
    scan        - Detect and log a license plate from a single image.
    batch-scan  - Process a directory of vehicle images and generate a summary.
    list        - Display vehicle logs, optionally filtered by date.
    search      - Search database logs for a specific license plate string.
    flag        - Blacklist or flag a license plate (or unflag).
    stats       - Display system dashboard summary statistics.
    export      - Export vehicle database logs to a CSV file.
"""

import argparse
import os
import sys
import time
from typing import Optional

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db_manager import DBManager
from src.detector import PlateDetector
from src.logger import logger
from src.ocr_reader import OCRReader
from src.utils import load_image, save_image

# Optional Rich formatting for enhanced terminal aesthetics
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    CONSOLE = Console()
    HAS_RICH = True
except ImportError:
    CONSOLE = None
    HAS_RICH = False


def print_banner():
    """Print welcoming CLI banner."""
    banner_text = """
========================================================================
   AUTOMATIC NUMBER PLATE RECOGNITION (ANPR) & VEHICLE LOG SYSTEM
       Classical Computer Vision Pipeline | SQLite Persistent DB
========================================================================
"""
    if HAS_RICH:
        CONSOLE.print(
            Panel.fit(
                "[bold cyan]AUTOMATIC NUMBER PLATE RECOGNITION (ANPR) & VEHICLE LOG SYSTEM[/bold cyan]\n"
                "[dim]Classical Computer Vision (OpenCV) | Multi-Engine OCR | SQLite Audit Log[/dim]",
                border_style="cyan",
            )
        )
    else:
        print(banner_text)


def handle_scan(args: argparse.Namespace, detector: PlateDetector, ocr: OCRReader, db: DBManager):
    """Execute plate detection and OCR on a single image."""
    image_path = os.path.abspath(args.image)
    if not os.path.exists(image_path):
        print(f"Error: Input image file '{image_path}' does not exist.")
        logger.error(f"CLI scan failed: file not found '{image_path}'")
        return 1

    print(f"\nProcessing image: {image_path}")
    start_time = time.perf_counter()

    # Step 1: Classical CV Plate Localization
    det_result = detector.detect(image_path)
    plate_crop = det_result.plate_crop

    # Step 2: OCR Extraction
    if det_result.is_detected and plate_crop is not None:
        ocr_result = ocr.read_plate(plate_crop)
        plate_number = ocr_result.clean_text
        confidence = ocr_result.confidence
        status = ocr_result.status
    else:
        plate_number = "UNREADABLE"
        confidence = 0.0
        status = "UNREADABLE"

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    # Step 3: Check Blacklist & Persist Log to SQLite
    is_flagged = db.is_plate_flagged(plate_number)
    log_id = db.insert_log(
        plate_number=plate_number,
        confidence=confidence,
        image_path=image_path,
        flagged=1 if is_flagged else 0,
        status=status,
    )

    # Save cropped plate if requested
    saved_crop_path = None
    if args.save_crop and plate_crop is not None:
        saved_crop_path = save_image(plate_crop, args.save_crop)

    # Render Result
    if HAS_RICH:
        table = Table(title="Scan Result Details", border_style="green" if status == "DETECTED" else "red")
        table.add_column("Property", style="bold")
        table.add_column("Value")

        table.add_row("Log Record ID", str(log_id))
        table.add_row(
            "Plate Number",
            f"[bold magenta]{plate_number}[/bold magenta]" if status == "DETECTED" else "[bold red]UNREADABLE[/bold red]",
        )
        table.add_row("Detection Status", f"[bold green]{status}[/bold green]" if status == "DETECTED" else "[bold red]UNREADABLE[/bold red]")
        table.add_row("Confidence Score", f"{confidence:.2f}")
        table.add_row(
            "Watchlist Status",
            "[bold red]!! FLAGGED / BLACKLISTED !![/bold red]" if is_flagged else "[green]CLEAN[/green]",
        )
        table.add_row("CPU Processing Time", f"{elapsed_ms:.1f} ms")
        table.add_row("Source Image", image_path)
        if saved_crop_path:
            table.add_row("Saved Crop", saved_crop_path)

        CONSOLE.print(table)
    else:
        print("\n--- Scan Result ---")
        print(f"Log ID:          {log_id}")
        print(f"Plate Number:    {plate_number}")
        print(f"Status:          {status}")
        print(f"Confidence:      {confidence:.2f}")
        print(f"Watchlist:       {'!! FLAGGED / BLACKLISTED !!' if is_flagged else 'CLEAN'}")
        print(f"CPU Time:        {elapsed_ms:.1f} ms")
        if saved_crop_path:
            print(f"Saved Crop:      {saved_crop_path}")

    return 0


def handle_batch_scan(args: argparse.Namespace, detector: PlateDetector, ocr: OCRReader, db: DBManager):
    """Scan all vehicle images in a folder and output a consolidated summary."""
    directory = os.path.abspath(args.dir)
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        return 1

    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    image_files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.splitext(f)[1].lower() in valid_exts
    ]

    if not image_files:
        print(f"No supported image files found in '{directory}'.")
        return 0

    print(f"\nDiscovered {len(image_files)} images in '{directory}'. Beginning batch scan...\n")

    results = []
    total_time = 0.0

    for idx, img_path in enumerate(sorted(image_files), 1):
        filename = os.path.basename(img_path)
        t0 = time.perf_counter()

        det_result = detector.detect(img_path)
        if det_result.is_detected and det_result.plate_crop is not None:
            ocr_res = ocr.read_plate(det_result.plate_crop)
            plate_num = ocr_res.clean_text
            conf = ocr_res.confidence
            stat = ocr_res.status
        else:
            plate_num = "UNREADABLE"
            conf = 0.0
            stat = "UNREADABLE"

        duration = (time.perf_counter() - t0) * 1000.0
        total_time += duration

        is_flagged = db.is_plate_flagged(plate_num)
        log_id = db.insert_log(
            plate_number=plate_num,
            confidence=conf,
            image_path=img_path,
            flagged=1 if is_flagged else 0,
            status=stat,
        )

        results.append({
            "id": log_id,
            "filename": filename,
            "plate": plate_num,
            "conf": conf,
            "status": stat,
            "flagged": is_flagged,
            "time_ms": duration,
        })

    # Display Batch Results Table
    if HAS_RICH:
        table = Table(title=f"Batch Scan Summary ({len(image_files)} images)", border_style="cyan")
        table.add_column("ID", justify="right")
        table.add_column("File")
        table.add_column("Plate Number", style="bold magenta")
        table.add_column("Confidence", justify="right")
        table.add_column("Status")
        table.add_column("Watchlist")
        table.add_column("Time (ms)", justify="right")

        for r in results:
            table.add_row(
                str(r["id"]),
                r["filename"],
                r["plate"],
                f"{r['conf']:.2f}",
                f"[green]{r['status']}[/green]" if r["status"] == "DETECTED" else "[red]UNREADABLE[/red]",
                "[bold red]FLAGGED[/bold red]" if r["flagged"] else "[green]CLEAN[/green]",
                f"{r['time_ms']:.1f}",
            )
        CONSOLE.print(table)
    else:
        print("\n" + "=" * 70)
        print(f"{'ID':<5} | {'Filename':<22} | {'Plate':<12} | {'Conf':<6} | {'Status':<10} | {'Watchlist':<8}")
        print("-" * 70)
        for r in results:
            print(
                f"{r['id']:<5} | {r['filename']:<22} | {r['plate']:<12} | {r['conf']:<6.2f} | "
                f"{r['status']:<10} | {'FLAGGED' if r['flagged'] else 'CLEAN'}"
            )
        print("=" * 70)

    avg_ms = total_time / len(image_files)
    print(f"\nBatch completed: {len(results)} images processed in {total_time:.1f} ms (Avg: {avg_ms:.1f} ms/frame).")

    if args.output_csv:
        db.export_to_csv(args.output_csv)
        print(f"Batch log results exported to: {os.path.abspath(args.output_csv)}")

    return 0


def handle_list(args: argparse.Namespace, db: DBManager):
    """List vehicle logs with optional date filter."""
    records = db.get_logs(date_str=args.date, limit=args.limit, offset=args.offset)
    title_suffix = f"for Date: {args.date}" if args.date else "Recent Detections"

    if not records:
        print(f"No records found {title_suffix}.")
        return 0

    if HAS_RICH:
        table = Table(title=f"Vehicle Audit Log ({title_suffix})", border_style="blue")
        table.add_column("ID", justify="right")
        table.add_column("Timestamp", style="dim")
        table.add_column("Plate Number", style="bold magenta")
        table.add_column("Confidence", justify="right")
        table.add_column("Status")
        table.add_column("Watchlist")
        table.add_column("Image Path", overflow="ellipsis")

        for r in records:
            table.add_row(
                str(r["id"]),
                str(r["timestamp"]),
                r["plate_number"],
                f"{r['confidence']:.2f}",
                f"[green]{r['status']}[/green]" if r["status"] == "DETECTED" else "[red]UNREADABLE[/red]",
                "[bold red]FLAGGED[/bold red]" if r["flagged"] else "[green]CLEAN[/green]",
                r["image_path"],
            )
        CONSOLE.print(table)
    else:
        print(f"\n--- Vehicle Audit Log ({title_suffix}) ---")
        for r in records:
            flag_str = "[FLAGGED]" if r["flagged"] else "[CLEAN]"
            print(
                f"[{r['id']}] {r['timestamp']} | {r['plate_number']} | Conf: {r['confidence']:.2f} | "
                f"{r['status']} | {flag_str} | {r['image_path']}"
            )
    return 0


def handle_search(args: argparse.Namespace, db: DBManager):
    """Search logs by plate number."""
    query = args.plate.strip().upper()
    records = db.search_by_plate(query, exact=args.exact)

    if not records:
        print(f"No log records found matching '{query}'.")
        return 0

    print(f"\nFound {len(records)} record(s) matching '{query}':")
    if HAS_RICH:
        table = Table(border_style="magenta")
        table.add_column("ID", justify="right")
        table.add_column("Timestamp")
        table.add_column("Plate Number", style="bold magenta")
        table.add_column("Confidence", justify="right")
        table.add_column("Watchlist")
        table.add_column("Image Path")

        for r in records:
            table.add_row(
                str(r["id"]),
                str(r["timestamp"]),
                r["plate_number"],
                f"{r['confidence']:.2f}",
                "[bold red]FLAGGED[/bold red]" if r["flagged"] else "[green]CLEAN[/green]",
                r["image_path"],
            )
        CONSOLE.print(table)
    else:
        for r in records:
            flag_str = "[FLAGGED]" if r["flagged"] else "[CLEAN]"
            print(f"[{r['id']}] {r['timestamp']} | {r['plate_number']} | Conf: {r['confidence']:.2f} | {flag_str} | {r['image_path']}")
    return 0


def handle_flag(args: argparse.Namespace, db: DBManager):
    """Flag or unflag a vehicle plate."""
    plate = args.plate.strip().upper()
    flag_bool = not args.unflag
    affected = db.set_flag(plate, flagged=flag_bool)

    action = "FLAGGED / BLACKLISTED" if flag_bool else "UNFLAGGED / REMOVED FROM BLACKLIST"
    print(f"\nPlate '{plate}' has been successfully {action}.")
    print(f"Database rows updated/created: {affected}")
    return 0


def handle_stats(db: DBManager):
    """Display dashboard statistics."""
    stats = db.get_summary_stats()

    if HAS_RICH:
        table = Table(title="ANPR System Dashboard Metrics", border_style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Plate Scans Recorded", str(stats["total_scans"]))
        table.add_row("Scans Logged Today", str(stats["today_scans"]))
        table.add_row("Watchlist / Flagged Vehicles", f"[bold red]{stats['flagged_count']}[/bold red]")
        table.add_row("Unreadable / Corrupt Scans", f"[yellow]{stats['unreadable_count']}[/yellow]")
        table.add_row("Average Recognition Confidence", f"[bold green]{stats['avg_confidence']:.2f}[/bold green]")

        CONSOLE.print(table)
    else:
        print("\n--- System Summary Metrics ---")
        print(f"Total Scans:        {stats['total_scans']}")
        print(f"Scans Today:        {stats['today_scans']}")
        print(f"Flagged Vehicles:   {stats['flagged_count']}")
        print(f"Unreadable Scans:   {stats['unreadable_count']}")
        print(f"Average Confidence: {stats['avg_confidence']:.2f}")
    return 0


def handle_export(args: argparse.Namespace, db: DBManager):
    """Export vehicle database records to CSV."""
    output_path = args.output
    exported = db.export_to_csv(output_path)
    print(f"\nDatabase logs exported successfully to:\n{exported}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build command-line interface argument parser."""
    parser = argparse.ArgumentParser(
        prog="anpr",
        description="Automatic Number Plate Recognition (ANPR) & Vehicle Log System",
        epilog="Use 'python main.py <command> --help' for command-specific options.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: scan
    scan_parser = subparsers.add_parser("scan", help="Scan a single vehicle image")
    scan_parser.add_argument("--image", "-i", required=True, help="Path to input vehicle image")
    scan_parser.add_argument("--save-crop", "-s", help="Optional path to save cropped plate image")
    scan_parser.add_argument("--engine", choices=["auto", "easyocr", "tesseract", "fallback"], default="auto", help="OCR engine preference")

    # Command: batch-scan
    batch_parser = subparsers.add_parser("batch-scan", help="Process a directory of images")
    batch_parser.add_argument("--dir", "-d", required=True, help="Directory containing vehicle images")
    batch_parser.add_argument("--output-csv", "-o", help="Optional path to export batch results to CSV")
    batch_parser.add_argument("--engine", choices=["auto", "easyocr", "tesseract", "fallback"], default="auto", help="OCR engine preference")

    # Command: list
    list_parser = subparsers.add_parser("list", help="List vehicle logs")
    list_parser.add_argument("--date", help="Filter by date (YYYY-MM-DD)")
    list_parser.add_argument("--limit", type=int, default=50, help="Maximum number of rows to return")
    list_parser.add_argument("--offset", type=int, default=0, help="Number of rows to skip")

    # Command: search
    search_parser = subparsers.add_parser("search", help="Search logs for a license plate")
    search_parser.add_argument("--plate", "-p", required=True, help="Plate string or substring to find")
    search_parser.add_argument("--exact", action="store_true", help="Match plate string exactly")

    # Command: flag
    flag_parser = subparsers.add_parser("flag", help="Blacklist or flag a license plate")
    flag_parser.add_argument("--plate", "-p", required=True, help="License plate number to flag/unflag")
    flag_parser.add_argument("--unflag", action="store_true", help="Remove flag/un-blacklist the plate")

    # Command: stats
    subparsers.add_parser("stats", help="Display system dashboard summary metrics")

    # Command: export
    export_parser = subparsers.add_parser("export", help="Export logs to CSV file")
    export_parser.add_argument("--output", "-o", default="data/vehicle_logs_export.csv", help="Target CSV filepath")

    return parser


def main():
    """Main CLI entry point."""
    parser = build_parser()
    if len(sys.argv) == 1:
        print_banner()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Centralized instances
    db = DBManager()
    detector = PlateDetector()

    # Route subcommands
    if args.command == "scan":
        ocr = OCRReader(preferred_engine=args.engine)
        sys.exit(handle_scan(args, detector, ocr, db))
    elif args.command == "batch-scan":
        ocr = OCRReader(preferred_engine=args.engine)
        sys.exit(handle_batch_scan(args, detector, ocr, db))
    elif args.command == "list":
        sys.exit(handle_list(args, db))
    elif args.command == "search":
        sys.exit(handle_search(args, db))
    elif args.command == "flag":
        sys.exit(handle_flag(args, db))
    elif args.command == "stats":
        sys.exit(handle_stats(db))
    elif args.command == "export":
        sys.exit(handle_export(args, db))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
