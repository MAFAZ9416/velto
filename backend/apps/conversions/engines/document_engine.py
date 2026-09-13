"""
Shared Document Conversion Engine for VELTO Conversion.

Supported Conversions:
  - TXT → PDF
  - TXT → DOCX
  - HTML → PDF
  - HTML → DOCX
  - Markdown → PDF
  - Markdown → DOCX

Architecture:
  Input (TXT / HTML / Markdown)
       ↓
  Decoding & Sanitization
       ↓
  Shared Document Representation (Block Tree)
       ↓
  PDF Renderer (ReportLab) OR DOCX Renderer (python-docx)
"""

import html
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import xml.sax.saxutils as saxutils

from django.conf import settings
from apps.conversions.engines.base import BaseConversionEngine, ConversionError
from apps.conversions.engines.validators import (
    validate_docx_output,
    validate_html_signature,
    validate_md_signature,
    validate_pdf_output,
    validate_txt_signature,
)
from apps.conversions.formats import (
    FORMAT_DOCX,
    FORMAT_HTML,
    FORMAT_MD,
    FORMAT_PDF,
    FORMAT_TXT,
)

# ── Safety Limits ─────────────────────────────────────────────────────────────
MAX_INPUT_BYTES = 52_428_800       # 50 MB
MAX_TEXT_LENGTH = 5_000_000        # 5 Million Chars (~5 MB text)
MAX_HTML_ELEMENTS = 50_000
MAX_TABLE_ROWS = 1_000
MAX_TABLE_COLS = 100
MAX_LIST_ITEMS = 10_000
MAX_PDF_PAGES = 500

# ── ReportLab & Font Setup ───────────────────────────────────────────────────
_UNICODE_FONT_NAME = None


def get_unicode_font_name() -> str:
    """
    Find and register a TrueType Unicode font for ReportLab.
    Supports Tamil, Hindi, Arabic, CJK, and standard Latin.
    Falls back to 'Helvetica' if no TTF Unicode font is available.
    """
    global _UNICODE_FONT_NAME
    if _UNICODE_FONT_NAME is not None:
        return _UNICODE_FONT_NAME

    candidate_paths = [
        "C:/Windows/Fonts/latha.ttf",
        "C:/Windows/Fonts/Nirmala.ttc",
        "C:/Windows/Fonts/NotoSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansTamil-Regular.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]

    font_path = None
    for p in candidate_paths:
        if os.path.exists(p):
            font_path = p
            break

    if font_path:
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            font_name = "VeltoUnicodeFont"
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            _UNICODE_FONT_NAME = font_name
            return font_name
        except Exception:
            pass

    _UNICODE_FONT_NAME = "Helvetica"
    return _UNICODE_FONT_NAME


# ── Shared Internal Document Representation ─────────────────────────────────

class Run:
    def __init__(
        self,
        text: str,
        bold: bool = False,
        italic: bool = False,
        code: bool = False,
        link: str | None = None,
    ):
        self.text = text
        self.bold = bold
        self.italic = italic
        self.code = code
        self.link = link

    def __repr__(self):
        return f"Run({self.text!r}, bold={self.bold}, italic={self.italic}, code={self.code})"


class ParagraphBlock:
    def __init__(self, runs: list[Run] | None = None, align: str = "left"):
        self.runs = runs or []
        self.align = align


class HeadingBlock:
    def __init__(self, level: int, runs: list[Run] | None = None):
        self.level = min(max(level, 1), 6)
        self.runs = runs or []


class ListItem:
    def __init__(self, blocks: list | None = None):
        self.blocks = blocks or []


class ListBlock:
    def __init__(self, items: list[ListItem] | None = None, ordered: bool = False):
        self.items = items or []
        self.ordered = ordered


class QuoteBlock:
    def __init__(self, blocks: list | None = None):
        self.blocks = blocks or []


class CodeBlock:
    def __init__(self, code_text: str, language: str = ""):
        self.code_text = code_text
        self.language = language


class TableCell:
    def __init__(self, blocks: list | None = None, is_header: bool = False):
        self.blocks = blocks or []
        self.is_header = is_header


class TableRow:
    def __init__(self, cells: list[TableCell] | None = None):
        self.cells = cells or []


class TableBlock:
    def __init__(self, rows: list[TableRow] | None = None):
        self.rows = rows or []


class HorizontalRuleBlock:
    pass


class Document:
    def __init__(self, blocks: list | None = None):
        self.blocks = blocks or []


# ── Input Decoding & Sanitization ─────────────────────────────────────────────

class DocumentTextService:
    @staticmethod
    def decode_and_normalize(input_path: str) -> str:
        """
        Decode raw text input using utf-8-sig -> utf-8.
        Normalize line endings to '\\n'.
        """
        p = Path(input_path)
        if not p.exists() or not p.is_file():
            raise ConversionError("The uploaded input file does not exist.")

        size = p.stat().st_size
        if size == 0:
            raise ConversionError("Input file is empty (0 bytes).")
        if size > MAX_INPUT_BYTES:
            max_mb = MAX_INPUT_BYTES / (1024 * 1024)
            raise ConversionError(f"Input file exceeds maximum allowed size ({max_mb:.0f} MB).")

        try:
            with open(input_path, "rb") as f:
                raw_bytes = f.read()
        except OSError as exc:
            raise ConversionError("Cannot read the uploaded file.") from exc

        decoded_text = None
        for enc in ("utf-8-sig", "utf-8"):
            try:
                decoded_text = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if decoded_text is None:
            raise ConversionError("Input file contains invalid UTF-8 encoding.")

        # Normalize line endings
        text = decoded_text.replace("\r\n", "\n").replace("\r", "\n")

        if len(text) > MAX_TEXT_LENGTH:
            raise ConversionError("Input document text exceeds maximum allowed length limit.")

        return text

    @staticmethod
    def txt_to_document(text: str) -> Document:
        """Convert plain text into a Document representation."""
        lines = text.split("\n")
        blocks = []
        for line in lines:
            blocks.append(ParagraphBlock(runs=[Run(line)]))
        return Document(blocks=blocks)


# ── Security & Sanitizing HTML Parser ─────────────────────────────────────────

class SecurityHTMLParser(HTMLParser):
    """
    Parses untrusted HTML into a Document block tree.
    Strips scripts, styles, iframes, objects, embeds, metas, and event handlers.
    Blocks unsafe URL schemes (javascript:, file:, data:).
    """

    VOID_DISALLOWED_TAGS = {"embed", "meta", "link", "base", "input"}
    CONTAINER_DISALLOWED_TAGS = {
        "script", "style", "iframe", "object", "head", "applet", "form", "button", "textarea", "select"
    }
    DANGEROUS_SCHEMES = ("javascript:", "file:", "data:", "vbscript:")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.document = Document()
        self.element_count = 0
        self.ignore_depth = 0

        # State tracking
        self.block_stack = []      # Active container blocks
        self.inline_style_stack = []  # Active inline formatting dicts
        self.current_runs = []     # Runs for current paragraph/heading
        self.current_heading_level = None
        self.current_code_text = []
        self.in_pre = False

    def is_safe_url(self, url: str) -> bool:
        if not url:
            return False
        clean_url = url.strip().lower()
        if any(clean_url.startswith(scheme) for scheme in self.DANGEROUS_SCHEMES):
            return False
        # Block Windows drive letters or root filesystem access (e.g. C:\ or /etc/)
        if re.match(r"^[a-zA-Z]:[\\/]", clean_url) or clean_url.startswith(("\\\\", "/etc", "/var", "/usr")):
            return False
        return True

    def _flush_paragraph(self):
        if self.current_runs or self.current_heading_level is not None:
            if self.current_heading_level is not None:
                hb = HeadingBlock(level=self.current_heading_level, runs=list(self.current_runs))
                self._add_block(hb)
                self.current_heading_level = None
            else:
                pb = ParagraphBlock(runs=list(self.current_runs))
                self._add_block(pb)
            self.current_runs = []

    def _add_block(self, block):
        if self.block_stack:
            parent = self.block_stack[-1]
            if isinstance(parent, QuoteBlock):
                parent.blocks.append(block)
            elif isinstance(parent, ListItem):
                parent.blocks.append(block)
            elif isinstance(parent, TableCell):
                parent.blocks.append(block)
            else:
                self.document.blocks.append(block)
        else:
            self.document.blocks.append(block)

    def handle_starttag(self, tag, attrs):
        self.element_count += 1
        if self.element_count > MAX_HTML_ELEMENTS:
            raise ConversionError("HTML document contains too many elements (exceeds safety limit).")

        tag = tag.lower()
        if tag in self.VOID_DISALLOWED_TAGS:
            return

        if tag in self.CONTAINER_DISALLOWED_TAGS or self.ignore_depth > 0:
            self.ignore_depth += 1
            return


        # Sanitize attributes (strip any on* event handler)
        safe_attrs = {k.lower(): v for k, v in attrs if not k.lower().startswith("on")}

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush_paragraph()
            self.current_heading_level = int(tag[1])
        elif tag == "p":
            self._flush_paragraph()
        elif tag == "br":
            self.current_runs.append(Run("\n"))
        elif tag == "hr":
            self._flush_paragraph()
            self._add_block(HorizontalRuleBlock())
        elif tag in ("b", "strong"):
            self.inline_style_stack.append("bold")
        elif tag in ("i", "em"):
            self.inline_style_stack.append("italic")
        elif tag == "code" and not self.in_pre:
            self.inline_style_stack.append("code")
        elif tag == "a":
            href = safe_attrs.get("href", "")
            if self.is_safe_url(href):
                self.inline_style_stack.append(("link", href))
            else:
                self.inline_style_stack.append(("link", None))
        elif tag == "blockquote":
            self._flush_paragraph()
            qb = QuoteBlock()
            self.block_stack.append(qb)
        elif tag in ("ul", "ol"):
            self._flush_paragraph()
            lb = ListBlock(ordered=(tag == "ol"))
            self.block_stack.append(lb)
        elif tag == "li":
            self._flush_paragraph()
            item = ListItem()
            if self.block_stack and isinstance(self.block_stack[-1], ListBlock):
                self.block_stack[-1].items.append(item)
            self.block_stack.append(item)
        elif tag == "pre":
            self._flush_paragraph()
            self.in_pre = True
            self.current_code_text = []
        elif tag == "table":
            self._flush_paragraph()
            tb = TableBlock()
            self.block_stack.append(tb)
        elif tag == "tr":
            if self.block_stack and isinstance(self.block_stack[-1], TableBlock):
                tr = TableRow()
                self.block_stack[-1].rows.append(tr)
                self.block_stack.append(tr)
        elif tag in ("td", "th"):
            if self.block_stack and isinstance(self.block_stack[-1], TableRow):
                tc = TableCell(is_header=(tag == "th"))
                self.block_stack[-1].cells.append(tc)
                self.block_stack.append(tc)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.ignore_depth > 0:
            self.ignore_depth -= 1
            return

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p"):
            self._flush_paragraph()
        elif tag in ("b", "strong"):
            if "bold" in self.inline_style_stack:
                self.inline_style_stack.remove("bold")
        elif tag in ("i", "em"):
            if "italic" in self.inline_style_stack:
                self.inline_style_stack.remove("italic")
        elif tag == "code" and not self.in_pre:
            if "code" in self.inline_style_stack:
                self.inline_style_stack.remove("code")
        elif tag == "a":
            self.inline_style_stack = [s for s in self.inline_style_stack if not (isinstance(s, tuple) and s[0] == "link")]
        elif tag == "blockquote":
            self._flush_paragraph()
            if self.block_stack and isinstance(self.block_stack[-1], QuoteBlock):
                qb = self.block_stack.pop()
                self._add_block(qb)
        elif tag in ("ul", "ol"):
            self._flush_paragraph()
            if self.block_stack and isinstance(self.block_stack[-1], ListBlock):
                lb = self.block_stack.pop()
                self._add_block(lb)
        elif tag == "li":
            self._flush_paragraph()
            if self.block_stack and isinstance(self.block_stack[-1], ListItem):
                self.block_stack.pop()
        elif tag == "pre":
            self.in_pre = False
            code_str = "".join(self.current_code_text)
            self._add_block(CodeBlock(code_text=code_str))
            self.current_code_text = []
        elif tag == "table":
            self._flush_paragraph()
            if self.block_stack and isinstance(self.block_stack[-1], TableBlock):
                tb = self.block_stack.pop()
                self._add_block(tb)
        elif tag == "tr":
            self._flush_paragraph()
            if self.block_stack and isinstance(self.block_stack[-1], TableRow):
                self.block_stack.pop()
        elif tag in ("td", "th"):
            self._flush_paragraph()
            if self.block_stack and isinstance(self.block_stack[-1], TableCell):
                self.block_stack.pop()

    def handle_data(self, data):
        if self.ignore_depth > 0:
            return
        if self.in_pre:
            self.current_code_text.append(data)
            return

        bold = "bold" in self.inline_style_stack
        italic = "italic" in self.inline_style_stack
        code = "code" in self.inline_style_stack
        link = None
        for s in self.inline_style_stack:
            if isinstance(s, tuple) and s[0] == "link":
                link = s[1]
                break

        run = Run(text=data, bold=bold, italic=italic, code=code, link=link)
        self.current_runs.append(run)

    def get_document(self) -> Document:
        self._flush_paragraph()
        return self.document


class HtmlSanitizationService:
    @staticmethod
    def parse_html_to_document(html_content: str) -> Document:
        parser = SecurityHTMLParser()
        try:
            parser.feed(html_content)
            parser.close()
            return parser.get_document()
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError("HTML content is malformed or processable failure occurred.") from exc


class MarkdownRenderingService:
    @staticmethod
    def markdown_to_document(md_content: str) -> Document:
        import markdown
        try:
            html_output = markdown.markdown(
                md_content,
                extensions=["extra", "sane_lists", "tables", "fenced_code"]
            )
        except Exception as exc:
            raise ConversionError("Failed to parse Markdown document structure.") from exc

        return HtmlSanitizationService.parse_html_to_document(html_output)


# ── PDF Renderer (ReportLab Platypus) ─────────────────────────────────────────

class DocumentPdfRenderer:
    @staticmethod
    def render(document: Document, output_path: str) -> None:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, Preformatted
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        font_name = get_unicode_font_name()
        styles = getSampleStyleSheet()

        # Define custom document styles
        body_style = ParagraphStyle(
            "VeltoBody",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=6,
        )

        h_styles = {
            1: ParagraphStyle("VeltoH1", parent=body_style, fontSize=20, leading=24, spaceBefore=12, spaceAfter=8, fontName=font_name),
            2: ParagraphStyle("VeltoH2", parent=body_style, fontSize=16, leading=20, spaceBefore=10, spaceAfter=6, fontName=font_name),
            3: ParagraphStyle("VeltoH3", parent=body_style, fontSize=13, leading=17, spaceBefore=8, spaceAfter=4, fontName=font_name),
            4: ParagraphStyle("VeltoH4", parent=body_style, fontSize=11.5, leading=15, spaceBefore=6, spaceAfter=4, fontName=font_name),
            5: ParagraphStyle("VeltoH5", parent=body_style, fontSize=10.5, leading=14, spaceBefore=4, spaceAfter=2, fontName=font_name),
            6: ParagraphStyle("VeltoH6", parent=body_style, fontSize=9.5, leading=13, spaceBefore=4, spaceAfter=2, fontName=font_name),
        }

        quote_style = ParagraphStyle(
            "VeltoQuote",
            parent=body_style,
            fontName=font_name,
            fontSize=10,
            leading=14,
            leftIndent=18,
            textColor=colors.HexColor("#475569"),
            spaceBefore=6,
            spaceAfter=6,
        )

        code_style = ParagraphStyle(
            "VeltoCode",
            parent=body_style,
            fontName=font_name,
            fontSize=9,
            leading=12,
            backColor=colors.HexColor("#f1f5f9"),
            borderColor=colors.HexColor("#cbd5e1"),
            borderWidth=0.5,
            borderPadding=6,
            spaceBefore=6,
            spaceAfter=6,
        )

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        story = []

        def _escape_text(txt: str) -> str:
            return saxutils.escape(txt)

        def _runs_to_xml(runs: list[Run]) -> str:
            parts = []
            for r in runs:
                escaped = _escape_text(r.text)
                if r.bold:
                    escaped = f"<b>{escaped}</b>"
                if r.italic:
                    escaped = f"<i>{escaped}</i>"
                if r.code:
                    escaped = f'<font face="Courier" size="9" color="#0f172a">{escaped}</font>'
                parts.append(escaped)
            xml_str = "".join(parts).replace("\n", "<br/>")
            return xml_str if xml_str.strip() else "&nbsp;"

        def _render_blocks(blocks: list):
            for block in blocks:
                if isinstance(block, HeadingBlock):
                    xml = _runs_to_xml(block.runs)
                    story.append(Paragraph(xml, h_styles[block.level]))
                elif isinstance(block, ParagraphBlock):
                    xml = _runs_to_xml(block.runs)
                    story.append(Paragraph(xml, body_style))
                elif isinstance(block, ListBlock):
                    bullet_char = "• " if not block.ordered else None
                    for idx, item in enumerate(block.items, start=1):
                        prefix = f"{idx}. " if block.ordered else bullet_char
                        for b in item.blocks:
                            if isinstance(b, ParagraphBlock):
                                item_xml = prefix + _runs_to_xml(b.runs)
                                item_style = ParagraphStyle("VeltoList", parent=body_style, leftIndent=18)
                                story.append(Paragraph(item_xml, item_style))
                            else:
                                _render_blocks([b])
                elif isinstance(block, QuoteBlock):
                    for b in block.blocks:
                        if isinstance(b, ParagraphBlock):
                            xml = _runs_to_xml(b.runs)
                            story.append(Paragraph(xml, quote_style))
                        else:
                            _render_blocks([b])
                elif isinstance(block, CodeBlock):
                    escaped_code = _escape_text(block.code_text)
                    story.append(Preformatted(escaped_code, code_style))
                elif isinstance(block, HorizontalRuleBlock):
                    story.append(Spacer(1, 4))
                    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=6, spaceAfter=6))
                elif isinstance(block, TableBlock):
                    if not block.rows:
                        continue
                    table_data = []
                    for row in block.rows:
                        row_data = []
                        for cell in row.cells:
                            cell_story = []
                            for b in cell.blocks:
                                if isinstance(b, ParagraphBlock):
                                    cell_story.append(Paragraph(_runs_to_xml(b.runs), body_style))
                            row_data.append(cell_story or Paragraph("&nbsp;", body_style))
                        table_data.append(row_data)

                    t = Table(table_data)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, -1), font_name),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 6))

        _render_blocks(document.blocks)

        if not story:
            story.append(Paragraph("&nbsp;", body_style))

        try:
            doc.build(story)
        except Exception as exc:
            raise ConversionError("PDF rendering failed for the document structure.") from exc

        validate_pdf_output(output_path)


# ── DOCX Renderer (python-docx) ─────────────────────────────────────────────

class DocumentDocxRenderer:
    @staticmethod
    def render(document: Document, output_path: str) -> None:
        import docx
        from docx.shared import Pt, RGBColor, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = docx.Document()

        # Set page margins
        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)

        def _add_runs_to_paragraph(p, runs: list[Run]):
            for r in runs:
                run = p.add_run(r.text)
                if r.bold:
                    run.bold = True
                if r.italic:
                    run.italic = True
                if r.code:
                    run.font.name = "Courier New"
                    run.font.size = Pt(9.5)
                    run.font.color.rgb = RGBColor(15, 23, 42)

        def _render_blocks(blocks: list):
            for block in blocks:
                if isinstance(block, HeadingBlock):
                    doc.add_heading("".join(r.text for r in block.runs), level=block.level)
                elif isinstance(block, ParagraphBlock):
                    p = doc.add_paragraph()
                    _add_runs_to_paragraph(p, block.runs)
                elif isinstance(block, ListBlock):
                    style_name = 'List Bullet' if not block.ordered else 'List Number'
                    for item in block.items:
                        for b in item.blocks:
                            if isinstance(b, ParagraphBlock):
                                p = doc.add_paragraph(style=style_name)
                                _add_runs_to_paragraph(p, b.runs)
                            else:
                                _render_blocks([b])
                elif isinstance(block, QuoteBlock):
                    for b in block.blocks:
                        if isinstance(b, ParagraphBlock):
                            p = doc.add_paragraph(style='Quote')
                            _add_runs_to_paragraph(p, b.runs)
                        else:
                            _render_blocks([b])
                elif isinstance(block, CodeBlock):
                    p = doc.add_paragraph()
                    r = p.add_run(block.code_text)
                    r.font.name = "Courier New"
                    r.font.size = Pt(9.5)
                elif isinstance(block, HorizontalRuleBlock):
                    p = doc.add_paragraph("─" * 40)
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif isinstance(block, TableBlock):
                    if not block.rows:
                        continue
                    num_rows = len(block.rows)
                    num_cols = max(len(r.cells) for r in block.rows) if num_rows > 0 else 0
                    if num_cols == 0:
                        continue

                    table = doc.add_table(rows=num_rows, cols=num_cols)
                    table.style = 'Table Grid'
                    for r_idx, row in enumerate(block.rows):
                        for c_idx, cell in enumerate(row.cells):
                            if c_idx < num_cols:
                                cell_p = table.cell(r_idx, c_idx).paragraphs[0]
                                for b in cell.blocks:
                                    if isinstance(b, ParagraphBlock):
                                        _add_runs_to_paragraph(cell_p, b.runs)

        _render_blocks(document.blocks)

        try:
            doc.save(output_path)
        except Exception as exc:
            raise ConversionError("DOCX rendering failed for the document structure.") from exc

        validate_docx_output(output_path)


# ── Engine Implementations ────────────────────────────────────────────────────

class TxtToPdfEngine(BaseConversionEngine):
    source_format = FORMAT_TXT
    target_format = FORMAT_PDF
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        validate_txt_signature(input_path)
        text = DocumentTextService.decode_and_normalize(input_path)
        doc = DocumentTextService.txt_to_document(text)
        DocumentPdfRenderer.render(doc, output_path)
        return output_path


class TxtToDocxEngine(BaseConversionEngine):
    source_format = FORMAT_TXT
    target_format = FORMAT_DOCX
    output_extension = ".docx"
    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        validate_txt_signature(input_path)
        text = DocumentTextService.decode_and_normalize(input_path)
        doc = DocumentTextService.txt_to_document(text)
        DocumentDocxRenderer.render(doc, output_path)
        return output_path


class HtmlToPdfEngine(BaseConversionEngine):
    source_format = FORMAT_HTML
    target_format = FORMAT_PDF
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        validate_html_signature(input_path)
        html_str = DocumentTextService.decode_and_normalize(input_path)
        doc = HtmlSanitizationService.parse_html_to_document(html_str)
        DocumentPdfRenderer.render(doc, output_path)
        return output_path


class HtmlToDocxEngine(BaseConversionEngine):
    source_format = FORMAT_HTML
    target_format = FORMAT_DOCX
    output_extension = ".docx"
    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        validate_html_signature(input_path)
        html_str = DocumentTextService.decode_and_normalize(input_path)
        doc = HtmlSanitizationService.parse_html_to_document(html_str)
        DocumentDocxRenderer.render(doc, output_path)
        return output_path


class MarkdownToPdfEngine(BaseConversionEngine):
    source_format = FORMAT_MD
    target_format = FORMAT_PDF
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        validate_md_signature(input_path)
        md_str = DocumentTextService.decode_and_normalize(input_path)
        doc = MarkdownRenderingService.markdown_to_document(md_str)
        DocumentPdfRenderer.render(doc, output_path)
        return output_path


class MarkdownToDocxEngine(BaseConversionEngine):
    source_format = FORMAT_MD
    target_format = FORMAT_DOCX
    output_extension = ".docx"
    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        validate_md_signature(input_path)
        md_str = DocumentTextService.decode_and_normalize(input_path)
        doc = MarkdownRenderingService.markdown_to_document(md_str)
        DocumentDocxRenderer.render(doc, output_path)
        return output_path


