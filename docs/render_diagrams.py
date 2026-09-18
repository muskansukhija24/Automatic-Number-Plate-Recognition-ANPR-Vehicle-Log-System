"""
Diagram Renderer for ANPR System Documentation.
Generates 5 publication-ready PNG diagram figures:
1. architecture_diagram.png
2. use_case_diagram.png
3. class_diagram.png
4. sequence_diagram.png
5. er_diagram.png
"""

import os
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def save_fig(fig, output_path):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Generated diagram: {output_path}")


def render_architecture(output_path):
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # Colors
    bg_color = "#F8FAFC"
    border_color = "#334155"
    box_blue = "#E0F2FE"
    box_green = "#DCFCE7"
    box_purple = "#F3E8FF"
    box_amber = "#FEF3C7"
    box_rose = "#FFE4E6"

    # Title
    ax.text(5.5, 6.6, "ANPR System — End-to-End Architecture", ha="center", va="center",
            fontsize=16, fontweight="bold", color="#0F172A")

    # Layer 1: Ingestion
    ax.add_patch(patches.FancyBboxPatch((0.5, 4.8), 2.2, 1.4, boxstyle="round,pad=0.2",
                                        ec="#0284C7", fc=box_blue, lw=2))
    ax.text(1.6, 5.8, "Input Ingestion", ha="center", va="center", fontsize=11, fontweight="bold", color="#0369A1")
    ax.text(1.6, 5.2, "• Single Frame (.jpg)\n• Batch Directory\n• Camera Stream", ha="center", va="center", fontsize=9, color="#334155")

    # Layer 2: Classical CV Detection
    ax.add_patch(patches.FancyBboxPatch((3.2, 4.5), 4.6, 1.7, boxstyle="round,pad=0.2",
                                        ec="#16A34A", fc=box_green, lw=2))
    ax.text(5.5, 5.9, "Module 1: Classical CV Plate Localization", ha="center", va="center", fontsize=11, fontweight="bold", color="#15803D")
    ax.text(5.5, 5.1, "1. Grayscale & Scale Normalization  -->  2. Bilateral Noise Filter\n3. Black-Hat Morphological Transform  -->  4. Sobel Edges & Closing\n5. Aspect Ratio (1.8-7.5) & Extent  -->  6. 4-Pt Homography Deskew",
            ha="center", va="center", fontsize=8.5, color="#1E293B")

    # Layer 3: OCR Extraction
    ax.add_patch(patches.FancyBboxPatch((8.3, 4.8), 2.2, 1.4, boxstyle="round,pad=0.2",
                                        ec="#9333EA", fc=box_purple, lw=2))
    ax.text(9.4, 5.8, "Module 2: OCR", ha="center", va="center", fontsize=11, fontweight="bold", color="#7E22CE")
    ax.text(9.4, 5.2, "• EasyOCR / Tesseract\n• Positional Disambiguation\n• Regex Validation", ha="center", va="center", fontsize=8.5, color="#334155")

    # Layer 4: Storage & Watchlist
    ax.add_patch(patches.FancyBboxPatch((1.5, 1.6), 3.8, 1.8, boxstyle="round,pad=0.2",
                                        ec="#D97706", fc=box_amber, lw=2))
    ax.text(3.4, 3.0, "Module 3: Storage & Watchlist", ha="center", va="center", fontsize=11, fontweight="bold", color="#B45309")
    ax.text(3.4, 2.2, "• SQLite DB (`vehicle_logs.db`)\n• Indexed Plate & Timestamp\n• Real-Time Blacklist Matching\n• Rotating Logs (`logs/app.log`)",
            ha="center", va="center", fontsize=9, color="#451A03")

    # Layer 5: CLI Dashboard
    ax.add_patch(patches.FancyBboxPatch((6.0, 1.6), 3.8, 1.8, boxstyle="round,pad=0.2",
                                        ec="#E11D48", fc=box_rose, lw=2))
    ax.text(7.9, 3.0, "Module 4: CLI Presentation", ha="center", va="center", fontsize=11, fontweight="bold", color="#BE123C")
    ax.text(7.9, 2.2, "• Rich Terminal Dashboard\n• Subcommands: scan, batch, list,\n  search, flag, stats, export\n• CSV File Exporter",
            ha="center", va="center", fontsize=9, color="#4C0519")

    # Connectors
    ax.annotate("", xy=(3.2, 5.5), xytext=(2.7, 5.5), arrowprops=dict(arrowstyle="->", lw=2, color="#475569"))
    ax.annotate("", xy=(8.3, 5.5), xytext=(7.8, 5.5), arrowprops=dict(arrowstyle="->", lw=2, color="#475569"))
    ax.annotate("", xy=(3.4, 3.4), xytext=(8.8, 4.8), arrowprops=dict(arrowstyle="->", lw=2, color="#475569", connectionstyle="angle,angleA=-90,angleB=180,rad=10"))
    ax.annotate("", xy=(6.0, 2.5), xytext=(5.3, 2.5), arrowprops=dict(arrowstyle="<->", lw=2, color="#475569"))

    save_fig(fig, output_path)


def render_use_case(output_path):
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.5)
    ax.axis("off")

    # System boundary box
    ax.add_patch(patches.Rectangle((3.0, 0.4), 6.6, 5.6, ec="#475569", fc="#F8FAFC", lw=2, ls="--"))
    ax.text(6.3, 5.7, "ANPR System Boundary", ha="center", va="center", fontsize=12, fontweight="bold", color="#1E293B")

    # Actor
    ax.add_patch(patches.Circle((1.2, 3.8), 0.35, ec="#1E293B", fc="#E2E8F0", lw=2))
    ax.plot([1.2, 1.2], [3.45, 2.4], color="#1E293B", lw=2)  # body
    ax.plot([0.7, 1.7], [3.0, 3.0], color="#1E293B", lw=2)    # arms
    ax.plot([1.2, 0.7], [2.4, 1.5], color="#1E293B", lw=2)    # left leg
    ax.plot([1.2, 1.7], [2.4, 1.5], color="#1E293B", lw=2)    # right leg
    ax.text(1.2, 1.1, "Operator /\nSecurity Guard", ha="center", va="center", fontsize=10, fontweight="bold", color="#0F172A")

    # Use Cases
    use_cases = [
        (4.8, 5.0, "UC-1: Scan Single Image"),
        (7.8, 5.0, "UC-2: Batch Scan Directory"),
        (4.8, 3.7, "UC-3: List Logs by Date"),
        (7.8, 3.7, "UC-4: Search Plate Number"),
        (4.8, 2.4, "UC-5: Flag / Blacklist Plate"),
        (7.8, 2.4, "UC-6: View Dashboard Stats"),
        (4.8, 1.1, "UC-7: Export Audit to CSV"),
        (7.8, 1.1, "UC-8: Alert on Blacklist <<include>>"),
    ]

    for (x, y, label) in use_cases:
        is_include = "<<include>>" in label
        fc = "#FEF3C7" if is_include else "#E0F2FE"
        ec = "#D97706" if is_include else "#0284C7"
        ax.add_patch(patches.Ellipse((x, y), 2.5, 0.75, ec=ec, fc=fc, lw=1.5))
        ax.text(x, y, label, ha="center", va="center", fontsize=8.5, color="#0F172A")

        if not is_include:
            ax.plot([1.7, x - 1.25], [3.0, y], color="#94A3B8", lw=1.2, ls=":")

    # Include arrow from UC-1 to UC-8
    ax.annotate("<<include>>", xy=(7.8, 1.5), xytext=(5.3, 4.6),
                arrowprops=dict(arrowstyle="->", lw=1.2, color="#DC2626", ls="--"),
                fontsize=7.5, color="#DC2626", rotation=-42)

    save_fig(fig, output_path)


def render_class_diagram(output_path):
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7.5)
    ax.axis("off")

    ax.text(5.5, 7.1, "ANPR System — Class & Component Diagram", ha="center", va="center",
            fontsize=15, fontweight="bold", color="#0F172A")

    # PlateDetector
    ax.add_patch(patches.Rectangle((0.5, 3.8), 3.0, 2.9, ec="#0284C7", fc="#F0F9FF", lw=1.5))
    ax.text(2.0, 6.4, "PlateDetector", ha="center", va="center", fontsize=10, fontweight="bold", color="#0369A1")
    ax.plot([0.5, 3.5], [6.15, 6.15], color="#0284C7", lw=1)
    ax.text(0.6, 5.4, "- min_aspect_ratio: float\n- max_aspect_ratio: float\n- canonical_width: int\n- min_area_ratio: float", fontsize=8, color="#334155")
    ax.plot([0.5, 3.5], [4.7, 4.7], color="#0284C7", lw=1)
    ax.text(0.6, 4.2, "+ detect(image) -> Result\n- _detect_via_morphology()\n- _find_best_contour()", fontsize=8, color="#334155")

    # OCRReader
    ax.add_patch(patches.Rectangle((4.0, 3.8), 3.0, 2.9, ec="#9333EA", fc="#FAF5FF", lw=1.5))
    ax.text(5.5, 6.4, "OCRReader", ha="center", va="center", fontsize=10, fontweight="bold", color="#7E22CE")
    ax.plot([4.0, 7.0], [6.15, 6.15], color="#9333EA", lw=1)
    ax.text(4.1, 5.4, "- preferred_engine: str\n- ALPHA_CONFUSIONS: dict\n- NUMERIC_CONFUSIONS: dict\n- STRICT_PLATE_REGEX: re", fontsize=8, color="#334155")
    ax.plot([4.0, 7.0], [4.7, 4.7], color="#9333EA", lw=1)
    ax.text(4.1, 4.2, "+ read_plate(crop) -> OCRResult\n+ clean_plate_text(raw) -> str\n+ preprocess_plate(crop) -> list", fontsize=8, color="#334155")

    # DBManager
    ax.add_patch(patches.Rectangle((7.5, 3.8), 3.0, 2.9, ec="#D97706", fc="#FFFBEB", lw=1.5))
    ax.text(9.0, 6.4, "DBManager", ha="center", va="center", fontsize=10, fontweight="bold", color="#B45309")
    ax.plot([7.5, 10.5], [6.15, 6.15], color="#D97706", lw=1)
    ax.text(7.6, 5.5, "- db_path: str\n- _init_db()\n- _get_connection()", fontsize=8, color="#334155")
    ax.plot([7.5, 10.5], [5.0, 5.0], color="#D97706", lw=1)
    ax.text(7.6, 4.3, "+ insert_log(...) -> int\n+ get_logs(date) -> list\n+ search_by_plate(...) -> list\n+ set_flag(plate, bool) -> int\n+ get_summary_stats() -> dict\n+ export_to_csv(...) -> str", fontsize=7.5, color="#334155")

    # CLI / main.py
    ax.add_patch(patches.Rectangle((3.5, 0.6), 4.0, 2.3, ec="#E11D48", fc="#FFF1F2", lw=1.5))
    ax.text(5.5, 2.6, "CLI Controller (main.py)", ha="center", va="center", fontsize=10, fontweight="bold", color="#BE123C")
    ax.plot([3.5, 7.5], [2.35, 2.35], color="#E11D48", lw=1)
    ax.text(3.7, 1.4, "+ handle_scan(args)\n+ handle_batch_scan(args)\n+ handle_list(args)\n+ handle_search(args)\n+ handle_flag(args)\n+ handle_stats(args)\n+ handle_export(args)", fontsize=8, color="#334155")

    # Associations
    ax.annotate("", xy=(2.0, 3.8), xytext=(4.2, 2.9), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475569"))
    ax.annotate("", xy=(5.5, 3.8), xytext=(5.5, 2.9), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475569"))
    ax.annotate("", xy=(9.0, 3.8), xytext=(6.8, 2.9), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475569"))

    save_fig(fig, output_path)


def render_sequence(output_path):
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.5)
    ax.axis("off")

    ax.text(5.0, 6.1, "Sequence Diagram — Single Image Scan Flow", ha="center", va="center",
            fontsize=14, fontweight="bold", color="#0F172A")

    lifelines = [
        (1.0, "Operator"),
        (2.8, "main.py (CLI)"),
        (4.8, "PlateDetector"),
        (6.8, "OCRReader"),
        (8.8, "DBManager"),
    ]

    for (x, name) in lifelines:
        ax.add_patch(patches.Rectangle((x - 0.7, 5.3), 1.4, 0.5, ec="#334155", fc="#E2E8F0", lw=1))
        ax.text(x, 5.55, name, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#0F172A")
        ax.plot([x, x], [0.5, 5.3], color="#CBD5E1", lw=1, ls="--")

    messages = [
        (1.0, 2.8, 4.8, "1. scan --image car.jpg", True),
        (2.8, 4.8, 4.2, "2. detect(image)", True),
        (4.8, 2.8, 3.6, "3. PlateDetectionResult(crop)", False),
        (2.8, 6.8, 3.0, "4. read_plate(crop)", True),
        (6.8, 2.8, 2.4, "5. OCRResult('DL01AB1234', conf)", False),
        (2.8, 8.8, 1.8, "6. insert_log(plate, conf)", True),
        (8.8, 2.8, 1.2, "7. log_id = 42, is_flagged", False),
        (2.8, 1.0, 0.7, "8. Render Result Card Table", False),
    ]

    for (x1, x2, y, text, is_call) in messages:
        ls = "-" if is_call else "--"
        color = "#0369A1" if is_call else "#15803D"
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", lw=1.2, color=color, ls=ls))
        mid_x = (x1 + x2) / 2
        ax.text(mid_x, y + 0.12, text, ha="center", va="bottom", fontsize=7.5, color="#1E293B")

    save_fig(fig, output_path)


def render_er_diagram(output_path):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 5.5)
    ax.axis("off")

    ax.text(4.0, 5.0, "Entity-Relationship (ER) Diagram — SQLite Schema", ha="center", va="center",
            fontsize=13, fontweight="bold", color="#0F172A")

    # Table Box
    ax.add_patch(patches.Rectangle((1.5, 0.8), 5.0, 3.8, ec="#0284C7", fc="#F0F9FF", lw=2))
    ax.add_patch(patches.Rectangle((1.5, 3.9), 5.0, 0.7, ec="#0284C7", fc="#0284C7", lw=2))
    ax.text(4.0, 4.25, "TABLE: vehicle_logs", ha="center", va="center", fontsize=11, fontweight="bold", color="#FFFFFF")

    fields = [
        ("id", "INTEGER", "PK, AUTOINCREMENT"),
        ("plate_number", "TEXT", "NOT NULL, INDEXED"),
        ("timestamp", "DATETIME", "DEFAULT CURRENT_TIMESTAMP, INDEXED"),
        ("confidence", "REAL", "NOT NULL (0.00 to 1.00)"),
        ("image_path", "TEXT", "NOT NULL"),
        ("flagged", "INTEGER", "DEFAULT 0 (0=Clean, 1=Flagged), INDEXED"),
        ("status", "TEXT", "DEFAULT 'DETECTED'"),
    ]

    y = 3.5
    for (name, col_type, note) in fields:
        ax.text(1.8, y, name, fontsize=8.5, fontweight="bold", color="#0F172A")
        ax.text(3.5, y, col_type, fontsize=8, color="#0369A1")
        ax.text(4.7, y, f"({note})", fontsize=7.5, color="#64748B")
        ax.plot([1.5, 6.5], [y - 0.12, y - 0.12], color="#E2E8F0", lw=0.8)
        y -= 0.42

    save_fig(fig, output_path)


def main():
    docs_dir = os.path.dirname(os.path.abspath(__file__))
    render_architecture(os.path.join(docs_dir, "architecture_diagram.png"))
    render_use_case(os.path.join(docs_dir, "use_case_diagram.png"))
    render_class_diagram(os.path.join(docs_dir, "class_diagram.png"))
    render_sequence(os.path.join(docs_dir, "sequence_diagram.png"))
    render_er_diagram(os.path.join(docs_dir, "er_diagram.png"))
    print("All documentation diagram images generated successfully.")


if __name__ == "__main__":
    main()
