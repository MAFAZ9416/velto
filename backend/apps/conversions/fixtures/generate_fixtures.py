"""
PDF fixture generator for VELTO Conversion tests.

Generates real PDF files using reportlab so tests can exercise the actual
pdf2docx conversion engine — not mocks or synthetic bytes.

All fixtures are written to the fixtures/ directory alongside this script.
Run once to (re)generate:

    python -m apps.conversions.fixtures.generate_fixtures

Or they are created automatically by the test suite's setUpClass.
"""

import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def _require_reportlab():
    if not REPORTLAB_AVAILABLE:
        raise ImportError(
            "reportlab is required to generate test fixtures. "
            "Run: pip install reportlab"
        )


def generate_simple_text_pdf(path: Path) -> None:
    """Single-page PDF with plain text paragraphs."""
    _require_reportlab()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("VELTO Conversion — Test Document", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(
            "This is a single-page text PDF created for automated testing. "
            "It contains multiple sentences to verify that the pdf2docx engine "
            "correctly extracts and converts embedded text to an editable Word document.",
            styles["Normal"],
        ),
        Spacer(1, 0.3 * cm),
        Paragraph(
            "Second paragraph: Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            styles["Normal"],
        ),
    ]
    doc.build(story)


def generate_multipage_pdf(path: Path) -> None:
    """Multi-page PDF with text content spread across 3 pages."""
    _require_reportlab()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    for page_num in range(1, 4):
        story.append(Paragraph(f"Page {page_num} — VELTO Conversion Test", styles["Heading1"]))
        story.append(Spacer(1, 0.5 * cm))
        for para_num in range(1, 4):
            story.append(
                Paragraph(
                    f"Page {page_num}, Paragraph {para_num}: "
                    "This content is on multiple pages to verify that the conversion engine "
                    "handles page breaks correctly and produces a properly structured document.",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 0.3 * cm))
        # Force page break between sections
        from reportlab.platypus import PageBreak
        if page_num < 3:
            story.append(PageBreak())
    doc.build(story)


def generate_table_pdf(path: Path) -> None:
    """PDF containing a table to test table extraction quality."""
    _require_reportlab()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()

    table_data = [
        ["Format", "Source", "Target", "Engine", "Status"],
        ["PDF → Word", "pdf", "docx", "pdf2docx", "Available"],
        ["Word → PDF", "docx", "pdf", "LibreOffice", "Planned"],
        ["PDF → Excel", "pdf", "xlsx", "pdf2docx", "Planned"],
        ["PDF → Image", "pdf", "jpg/png", "PyMuPDF", "Planned"],
    ]

    table = Table(table_data, colWidths=[4 * cm, 3 * cm, 3 * cm, 4 * cm, 3 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F0F4F8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E8EEF4")]),
            ]
        )
    )

    story = [
        Paragraph("Supported Conversion Formats", styles["Title"]),
        Spacer(1, 0.5 * cm),
        table,
    ]
    doc.build(story)


def generate_image_pdf(path: Path) -> None:
    """PDF containing embedded text AND a simple embedded image."""
    _require_reportlab()
    import tempfile

    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()

    # Create a tiny synthetic image saved to a temp file (reportlab needs a path)
    try:
        from PIL import Image as PILImage
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        img = PILImage.new("RGB", (200, 100), color=(70, 130, 180))
        img.save(tmp_path, format="PNG")

        rl_image = Image(tmp_path, width=5 * cm, height=2.5 * cm)
        story = [
            Paragraph("PDF with Embedded Image", styles["Title"]),
            Spacer(1, 0.5 * cm),
            Paragraph(
                "This PDF contains both text and an embedded image. "
                "The conversion engine should preserve the text as editable "
                "and embed the image in the DOCX output.",
                styles["Normal"],
            ),
            Spacer(1, 0.5 * cm),
            rl_image,
            Spacer(1, 0.5 * cm),
            Paragraph("Caption: Sample colour block image.", styles["Normal"]),
        ]
        doc.build(story)
        # Clean up temp image file
        import os
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return
    except ImportError:
        pass

    # Pillow not available — generate text-only version
    story = [
        Paragraph("PDF with Image Reference (Pillow not installed)", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph("Text-only fallback: Pillow not installed.", styles["Normal"]),
    ]
    doc.build(story)


def generate_all_fixtures() -> dict[str, Path]:
    """
    Generate all fixture PDFs and return a dict mapping name → path.
    Skips generation if the file already exists.
    """
    fixtures = {
        "simple_text": FIXTURES_DIR / "simple_text.pdf",
        "multipage": FIXTURES_DIR / "multipage.pdf",
        "with_table": FIXTURES_DIR / "with_table.pdf",
        "with_image": FIXTURES_DIR / "with_image.pdf",
    }

    generators = {
        "simple_text": generate_simple_text_pdf,
        "multipage": generate_multipage_pdf,
        "with_table": generate_table_pdf,
        "with_image": generate_image_pdf,
    }

    for name, path in fixtures.items():
        if not path.exists():
            generators[name](path)
            print(f"Generated: {path}")
        else:
            print(f"Exists:    {path}")

    return fixtures


if __name__ == "__main__":
    generate_all_fixtures()
