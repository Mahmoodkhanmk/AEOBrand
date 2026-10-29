"""Build the AEOBrand graduate-level literature-survey PDF from its Markdown source."""

from pathlib import Path
import re
import html
import xml.sax.saxutils as saxutils

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, Flowable,
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "Literature_Survey_AEOBrand.md"
OUTPUT = ROOT / "Literature_Survey_AEOBrand.pdf"

# Register a Unicode-capable font when available; fall back to built-in fonts.
font_regular = "Helvetica"
font_bold = "Helvetica-Bold"
for regular_path, bold_path in [
    (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf")),
    (Path(r"C:\Windows\Fonts\calibri.ttf"), Path(r"C:\Windows\Fonts\calibrib.ttf")),
]:
    if regular_path.exists() and bold_path.exists():
        pdfmetrics.registerFont(TTFont("SurveySans", str(regular_path)))
        pdfmetrics.registerFont(TTFont("SurveySans-Bold", str(bold_path)))
        font_regular, font_bold = "SurveySans", "SurveySans-Bold"
        break

NAVY = colors.HexColor("#17324D")
TEAL = colors.HexColor("#0F766E")
INK = colors.HexColor("#25313B")
MUTED = colors.HexColor("#5B6873")
PALE = colors.HexColor("#EAF1F5")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="BodyAcademic", parent=styles["BodyText"], fontName=font_regular,
    fontSize=9.6, leading=14.2, textColor=INK, alignment=TA_JUSTIFY,
    spaceAfter=7.5, allowWidows=0, allowOrphans=0,
))
styles.add(ParagraphStyle(
    name="TitleCover", fontName=font_bold, fontSize=24, leading=30,
    textColor=NAVY, alignment=TA_CENTER, spaceAfter=12,
))
styles.add(ParagraphStyle(
    name="SubtitleCover", fontName=font_regular, fontSize=15, leading=21,
    textColor=TEAL, alignment=TA_CENTER, spaceAfter=12,
))
styles.add(ParagraphStyle(
    name="Heading1Academic", fontName=font_bold, fontSize=15, leading=19,
    textColor=NAVY, spaceBefore=12, spaceAfter=8, keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="Heading2Academic", fontName=font_bold, fontSize=11.2, leading=15,
    textColor=TEAL, spaceBefore=10, spaceAfter=5, keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="SmallAcademic", fontName=font_regular, fontSize=8.3, leading=11.2,
    textColor=MUTED, alignment=TA_LEFT, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="ReferenceAcademic", fontName=font_regular, fontSize=8.2, leading=11.4,
    textColor=INK, leftIndent=16, firstLineIndent=-16, spaceAfter=6,
    allowWidows=0, allowOrphans=0,
))
styles.add(ParagraphStyle(
    name="FigureCaption", fontName=font_regular, fontSize=8.4, leading=11.5,
    textColor=MUTED, alignment=TA_LEFT, spaceBefore=4, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="Callout", fontName=font_regular, fontSize=8.8, leading=12.4,
    textColor=NAVY, backColor=PALE, borderColor=colors.HexColor("#CBD8E0"),
    borderWidth=0.6, borderPadding=8, spaceBefore=5, spaceAfter=10,
))


def inline_markup(text: str) -> str:
    text = saxutils.escape(text, {'"': '&quot;'})
    # Markdown links; preserve URL as readable clickable text.
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
                  r'<link href="\2" color="#0F766E">\1</link>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    return text


class PipelineFigure(Flowable):
    def __init__(self, width=170 * mm, height=83 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        c.saveState()
        c.setFillColor(colors.HexColor("#F6F9FB"))
        c.setStrokeColor(colors.HexColor("#D5E0E7"))
        c.roundRect(0, 0, w, h, 5 * mm, stroke=1, fill=1)

        nodes = [
            ("1  CONFIGURE", "Brand, competitors,\nmarkets, intent"),
            ("2  SAMPLE", "Fixed panel +\nexploratory queries"),
            ("3  QUERY MODELS", "Matched prompts;\nprovider + time logged"),
            ("4  CAPTURE", "Raw responses, errors,\nsource metadata"),
            ("5  ANNOTATE", "Mentions, claims,\nsentiment, citations"),
            ("6  VALIDATE", "Human audit +\nmetric evaluation"),
            ("7  REPORT", "Rates, uncertainty,\nmodel breakdown"),
        ]
        left = 5 * mm
        top = h - 9 * mm
        boxw = w - 10 * mm
        boxh = 8.2 * mm
        gap = 2.2 * mm
        for i, (head, detail) in enumerate(nodes):
            y = top - (i + 1) * boxh - i * gap
            c.setFillColor(colors.white if i < 5 else colors.HexColor("#EDF6F4"))
            c.setStrokeColor(TEAL if i >= 5 else colors.HexColor("#A9BBC7"))
            c.roundRect(left, y, boxw, boxh, 2 * mm, stroke=1, fill=1)
            c.setFillColor(NAVY if i < 5 else TEAL)
            c.setFont(font_bold, 7.8)
            c.drawString(left + 3 * mm, y + 5.2 * mm, head)
            c.setFillColor(INK)
            c.setFont(font_regular, 7.4)
            c.drawString(left + 39 * mm, y + 5.2 * mm, detail.split("\n")[0])
            c.drawString(left + 39 * mm, y + 2.2 * mm, detail.split("\n")[1])
            if i < len(nodes) - 1:
                x = left + boxw / 2
                c.setStrokeColor(TEAL)
                c.setLineWidth(1)
                c.line(x, y, x, y - gap + 0.6 * mm)
                c.line(x, y - gap + 0.6 * mm, x - 1.2 * mm, y - gap + 1.8 * mm)
                c.line(x, y - gap + 0.6 * mm, x + 1.2 * mm, y - gap + 1.8 * mm)
        c.setFillColor(MUTED)
        c.setFont(font_regular, 7)
        c.drawRightString(w - 5 * mm, 3 * mm, "Dashed boundary in research: data collection → validated inference")
        c.restoreState()


class SurveyDocTemplate(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(filename, pagesize=A4, leftMargin=25 * mm, rightMargin=23 * mm,
                         topMargin=22 * mm, bottomMargin=20 * mm,
                         title="AEOBrand Literature Survey", author="AEOBrand Project Team",
                         subject="Graduate literature survey on generative answer visibility")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                      id="normal")
        self.addPageTemplates(PageTemplate(id="survey", frames=frame, onPage=self.decorate))

    def decorate(self, canvas, doc):
        canvas.saveState()
        page = canvas.getPageNumber()
        if page > 1:
            canvas.setStrokeColor(colors.HexColor("#D9E1E6"))
            canvas.line(25 * mm, A4[1] - 15 * mm, A4[0] - 23 * mm, A4[1] - 15 * mm)
            canvas.setFont(font_regular, 7.5)
            canvas.setFillColor(MUTED)
            canvas.drawString(25 * mm, A4[1] - 12 * mm, "AEOBrand | Literature Survey")
            canvas.drawRightString(A4[0] - 23 * mm, 12 * mm, f"{page}")
        canvas.restoreState()


def parse_markdown(text: str):
    lines = text.splitlines()
    story = []
    i = 0
    cover_done = False
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == "{FIGURE_PIPELINE}":
            story += [Spacer(1, 4), PipelineFigure(), Paragraph(
                '<b>Figure 1.</b> AEOBrand measurement workflow and validation boundary. '
                '<b>Source:</b> Authors’ illustration based on the AEOBrand project architecture '
                'and the literature reviewed in [1]–[12]; future/optional components are marked as such.',
                styles["FigureCaption"])]
            i += 1
            continue
        if line.startswith("# "):
            title = line[2:]
            if not cover_done:
                story += [Spacer(1, 46 * mm), Paragraph(inline_markup(title), styles["TitleCover"])]
                cover_done = True
            else:
                story.append(Paragraph(inline_markup(title), styles["Heading1Academic"]))
            i += 1
            continue
        if line.startswith("## "):
            title = line[3:]
            if title == "Literature Survey":
                story.append(Paragraph(inline_markup(title), styles["SubtitleCover"]))
                story.append(Spacer(1, 13 * mm))
                i += 1
                continue
            if title in ("Abstract", "Index Terms—"):
                story.append(PageBreak())
            story.append(Paragraph(inline_markup(title), styles["Heading1Academic"]))
            i += 1
            continue
        if line.startswith("### "):
            story.append(Paragraph(inline_markup(line[4:]), styles["Heading2Academic"]))
            i += 1
            continue
        if line.startswith("> "):
            text_callout = line[2:]
            story.append(Paragraph(inline_markup(text_callout), styles["Callout"]))
            i += 1
            continue
        if line.startswith("**") and line.endswith("**"):
            story.append(Paragraph(inline_markup(line), styles["SmallAcademic"]))
            i += 1
            continue
        # Cover metadata lines; render centered in a tidy block.
        if line.startswith("**Institution:**") or line.startswith("**Department:**") or line.startswith("**Programme:**") or line.startswith("**Submitted by:**") or line.startswith("**Guide:**") or line.startswith("**Date:**") or line.startswith("**Project area:**") or line.startswith("**Document type:**"):
            story.append(Paragraph(inline_markup(line), ParagraphStyle(
                name="CoverMeta", parent=styles["BodyAcademic"], alignment=TA_CENTER,
                fontSize=10.2, leading=16, spaceAfter=2, textColor=INK)))
            i += 1
            continue
        if line.startswith("[1]") or re.match(r"^\[\d+\]", line):
            block = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^\[\d+\]", lines[i].strip()):
                if lines[i].strip().startswith("[") and i > 0:
                    break
                block.append(lines[i].strip())
                i += 1
            story.append(Paragraph(inline_markup(" ".join(block)), styles["ReferenceAcademic"]))
            continue
        if line.startswith("- "):
            story.append(Paragraph("• " + inline_markup(line[2:]), styles["BodyAcademic"]))
            i += 1
            continue
        story.append(Paragraph(inline_markup(line), styles["BodyAcademic"]))
        i += 1
    return story


def main():
    markdown = SOURCE.read_text(encoding="utf-8")
    doc = SurveyDocTemplate(str(OUTPUT))
    doc.build(parse_markdown(markdown))
    print(f"Created {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
