import os
import json
import math
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4, LETTER
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab>=4.0", "-q"])
    from reportlab.lib.pagesizes import A4, LETTER
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── helpers ──────────────────────────────────────────────────────────────────

def get_page_size(size_str):
    return LETTER if str(size_str).upper() == "LETTER" else A4


def safe_filename(name):
    name = name or "document"
    name = name.replace(" ", "-").replace("/", "-").replace("\\", "-")
    if not name.endswith(".pdf"):
        name += ".pdf"
    return name


def file_size_kb(path):
    try:
        return round(os.path.getsize(path) / 1024, 1)
    except Exception:
        return 0


def count_pages(path):
    """Count pages in PDF by scanning %%EOF / page markers."""
    try:
        with open(path, "rb") as f:
            content = f.read()
        return content.count(b"/Page\n") + content.count(b"/Page\r") + content.count(b"/Page ")
    except Exception:
        return 1


def draw_footer(canvas, doc):
    """Draw 'oya.ai' footer on every page."""
    canvas.saveState()
    page_width, page_height = doc.pagesize
    footer_text = "oya.ai"
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#999999"))
    canvas.drawCentredString(page_width / 2.0, 1.0 * cm, footer_text)
    canvas.restoreState()


def base_doc(filepath, page_size, title="", author="", margins=None):
    margins = margins or {}
    doc = SimpleDocTemplate(
        filepath,
        pagesize=page_size,
        title=title,
        author=author,
        leftMargin=margins.get("left", 2.0) * cm,
        rightMargin=margins.get("right", 2.0) * cm,
        topMargin=margins.get("top", 2.0) * cm,
        bottomMargin=margins.get("bottom", 2.0) * cm,
    )
    return doc


def base_styles(font_size=12):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "BodyCustom",
        parent=styles["Normal"],
        fontSize=font_size,
        leading=font_size * 1.4,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "H1Custom",
        parent=styles["Heading1"],
        fontSize=font_size + 8,
        leading=(font_size + 8) * 1.3,
        spaceAfter=12,
        textColor=colors.HexColor("#1a1a2e"),
    ))
    styles.add(ParagraphStyle(
        "H2Custom",
        parent=styles["Heading2"],
        fontSize=font_size + 3,
        leading=(font_size + 3) * 1.3,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#16213e"),
    ))
    styles.add(ParagraphStyle(
        "CenteredTitle",
        parent=styles["Normal"],
        fontSize=font_size + 10,
        leading=(font_size + 10) * 1.3,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "SubTitle",
        parent=styles["Normal"],
        fontSize=font_size + 1,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        "RightAlign",
        parent=styles["Normal"],
        fontSize=font_size,
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        "SmallNote",
        parent=styles["Normal"],
        fontSize=max(8, font_size - 2),
        textColor=colors.HexColor("#666666"),
        spaceAfter=4,
    ))
    return styles


# ── action handlers ───────────────────────────────────────────────────────────

def do_text_to_pdf(inp):
    content = inp.get("content", "")
    if not content:
        return {"error": "Provide 'content' text to convert to PDF"}

    filename = safe_filename(inp.get("filename", "document"))
    title = inp.get("title", "Document")
    author = inp.get("author", "")
    font_size = max(8, min(24, int(inp.get("font_size", 12))))
    page_size = get_page_size(inp.get("page_size", "A4"))

    doc = base_doc(filename, page_size, title=title, author=author)
    styles = base_styles(font_size)
    story = []

    if title:
        story.append(Paragraph(title, styles["CenteredTitle"]))
    if author:
        story.append(Paragraph(f"By {author}", styles["SubTitle"]))
    if title or author:
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
        story.append(Spacer(1, 0.4 * cm))

    for para in content.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        # detect headings (short lines ending without period)
        if len(para) < 80 and not para.endswith(".") and "\n" not in para and para.isupper():
            story.append(Paragraph(para, styles["H2Custom"]))
        else:
            text = para.replace("\n", "<br/>")
            story.append(Paragraph(text, styles["BodyCustom"]))
            story.append(Spacer(1, 0.2 * cm))

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    print(f"A2ABASEAI_FILE: {filename}")
    return {
        "status": "ok",
        "filename": filename,
        "filepath": filename,
        "title": title,
        "pages": max(1, count_pages(filename)),
        "file_size_kb": file_size_kb(filename),
    }


def do_invoice_pdf(inp):
    inv = inp.get("invoice_data", {})
    if not inv:
        return {"error": "Provide 'invoice_data' object with from, to, items fields"}
    items = inv.get("items", [])
    if not items:
        return {"error": "invoice_data must contain at least one item in 'items' list"}

    filename = safe_filename(inp.get("filename", "invoice"))
    currency = inv.get("currency", "USD")
    currency_sym = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CAD": "CA$"}.get(currency, currency + " ")
    page_size = get_page_size(inp.get("page_size", "A4"))

    doc = base_doc(filename, page_size, title=f"Invoice {inv.get('invoice_number', '')}", margins={"left": 1.8, "right": 1.8, "top": 1.8, "bottom": 1.8})
    styles = base_styles(10)
    story = []

    # Header
    header_data = [
        [Paragraph("<b><font size=22 color='#1a1a2e'>INVOICE</font></b>", styles["Normal"]),
         Paragraph(f"<b>Invoice #</b> {inv.get('invoice_number', 'N/A')}<br/>"
                   f"<b>Date:</b> {inv.get('date', datetime.today().strftime('%Y-%m-%d'))}<br/>"
                   f"<b>Due:</b> {inv.get('due_date', 'Upon receipt')}", styles["RightAlign"])]
    ]
    header_tbl = Table(header_data, colWidths=["60%", "40%"])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(header_tbl)
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.4 * cm))

    # Bill From / To
    from_text = inv.get("from", "").replace("\n", "<br/>")
    to_text = inv.get("to", "").replace("\n", "<br/>")
    addr_data = [
        [Paragraph("<b>From</b>", styles["BodyCustom"]), Paragraph("<b>To</b>", styles["BodyCustom"])],
        [Paragraph(from_text, styles["BodyCustom"]), Paragraph(to_text, styles["BodyCustom"])],
    ]
    addr_tbl = Table(addr_data, colWidths=["50%", "50%"])
    addr_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#555555")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(addr_tbl)
    story.append(Spacer(1, 0.5 * cm))

    # Line items table
    col_headers = ["Description", "Qty", "Unit Price", "Amount"]
    table_rows = [col_headers]
    subtotal = 0.0
    for item in items:
        qty = float(item.get("quantity", 1))
        price = float(item.get("unit_price", 0))
        amount = qty * price
        subtotal += amount
        table_rows.append([
            item.get("description", ""),
            str(int(qty)) if qty == int(qty) else f"{qty:.2f}",
            f"{currency_sym}{price:,.2f}",
            f"{currency_sym}{amount:,.2f}",
        ])

    tax_rate = float(inv.get("tax_rate", 0))
    tax_amount = subtotal * tax_rate / 100
    total = subtotal + tax_amount

    table_rows.append(["", "", "Subtotal", f"{currency_sym}{subtotal:,.2f}"])
    if tax_rate:
        table_rows.append(["", "", f"Tax ({tax_rate:.1f}%)", f"{currency_sym}{tax_amount:,.2f}"])
    table_rows.append(["", "", Paragraph("<b>TOTAL</b>", styles["RightAlign"]),
                        Paragraph(f"<b>{currency_sym}{total:,.2f}</b>", styles["RightAlign"])])

    pw = doc.width
    items_tbl = Table(table_rows, colWidths=[pw * 0.5, pw * 0.1, pw * 0.2, pw * 0.2])
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -3), [colors.white, colors.HexColor("#f5f5f5")]),
        ("GRID", (0, 0), (-1, -4), 0.5, colors.HexColor("#dddddd")),
        ("LINEABOVE", (0, -3), (-1, -3), 1, colors.HexColor("#cccccc")),
        ("LINEABOVE", (2, -1), (-1, -1), 2, colors.HexColor("#1a1a2e")),
        ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("SPAN", (0, -1), (1, -1)),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 0.6 * cm))

    if inv.get("notes"):
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("<b>Notes</b>", styles["SmallNote"]))
        story.append(Paragraph(inv["notes"], styles["SmallNote"]))

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    print(f"A2ABASEAI_FILE: {filename}")
    return {
        "status": "ok",
        "filename": filename,
        "filepath": filename,
        "invoice_number": inv.get("invoice_number", ""),
        "subtotal": round(subtotal, 2),
        "total": round(total, 2),
        "currency": currency,
        "pages": max(1, count_pages(filename)),
        "file_size_kb": file_size_kb(filename),
    }


def do_report_pdf(inp):
    title = inp.get("title", "Report")
    content = inp.get("content", "")
    sections = inp.get("sections", [])
    if not content and not sections:
        return {"error": "Provide 'content' summary text and/or 'sections' list [{heading, body}]"}

    filename = safe_filename(inp.get("filename", "report"))
    author = inp.get("author", "")
    font_size = max(8, min(24, int(inp.get("font_size", 12))))
    page_size = get_page_size(inp.get("page_size", "A4"))

    doc = base_doc(filename, page_size, title=title, author=author)
    styles = base_styles(font_size)
    story = []

    # Cover block
    story.append(Spacer(1, 1.0 * cm))
    story.append(Paragraph(title, styles["CenteredTitle"]))
    meta_parts = []
    if author:
        meta_parts.append(f"Author: {author}")
    meta_parts.append(datetime.today().strftime("%B %d, %Y"))
    story.append(Paragraph(" &nbsp;|&nbsp; ".join(meta_parts), styles["SubTitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.5 * cm))

    if content:
        story.append(Paragraph("<b>Executive Summary</b>", styles["H2Custom"]))
        for para in content.split("\n\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para.replace("\n", "<br/>"), styles["BodyCustom"]))
        story.append(Spacer(1, 0.4 * cm))

    for i, section in enumerate(sections, 1):
        heading = section.get("heading", f"Section {i}")
        body = section.get("body", "")
        block = []
        block.append(Paragraph(f"{i}. {heading}", styles["H2Custom"]))
        if body:
            for para in body.split("\n\n"):
                para = para.strip()
                if para:
                    block.append(Paragraph(para.replace("\n", "<br/>"), styles["BodyCustom"]))
        block.append(Spacer(1, 0.3 * cm))
        story.append(KeepTogether(block))

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    print(f"A2ABASEAI_FILE: {filename}")
    return {
        "status": "ok",
        "filename": filename,
        "filepath": filename,
        "title": title,
        "sections_count": len(sections),
        "pages": max(1, count_pages(filename)),
        "file_size_kb": file_size_kb(filename),
    }


def do_table_pdf(inp):
    table_data = inp.get("table_data", {})
    headers = table_data.get("headers", [])
    rows = table_data.get("rows", [])
    if not headers or not rows:
        return {"error": "Provide 'table_data' with 'headers' list and 'rows' list of lists"}

    filename = safe_filename(inp.get("filename", "table"))
    title = inp.get("title", "Data Table")
    caption = table_data.get("caption", "")
    page_size = get_page_size(inp.get("page_size", "A4"))
    font_size = max(8, min(24, int(inp.get("font_size", 10))))

    doc = base_doc(filename, page_size, title=title, margins={"left": 1.5, "right": 1.5, "top": 1.8, "bottom": 1.8})
    styles = base_styles(font_size)
    story = []

    story.append(Paragraph(title, styles["CenteredTitle"]))
    if caption:
        story.append(Paragraph(caption, styles["SubTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.4 * cm))

    all_rows = [headers] + [list(row) for row in rows]
    n_cols = len(headers)
    col_width = doc.width / n_cols

    tbl = Table(all_rows, colWidths=[col_width] * n_cols, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), font_size),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"<i>{len(rows)} row(s) &nbsp;|&nbsp; {n_cols} column(s)</i>", styles["SmallNote"]))

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    print(f"A2ABASEAI_FILE: {filename}")
    return {
        "status": "ok",
        "filename": filename,
        "filepath": filename,
        "title": title,
        "rows_count": len(rows),
        "columns_count": n_cols,
        "pages": max(1, count_pages(filename)),
        "file_size_kb": file_size_kb(filename),
    }


# ── main dispatch ─────────────────────────────────────────────────────────────

try:
    inp = json.loads(os.environ.get("INPUT_JSON", "{}"))
    action = inp.get("action", "")

    if action == "text_to_pdf":
        result = do_text_to_pdf(inp)
    elif action == "invoice_pdf":
        result = do_invoice_pdf(inp)
    elif action == "report_pdf":
        result = do_report_pdf(inp)
    elif action == "table_pdf":
        result = do_table_pdf(inp)
    else:
        result = {
            "error": f"Unknown action: '{action}'. Available: text_to_pdf, invoice_pdf, report_pdf, table_pdf"
        }

    print(json.dumps(result))
except Exception as e:
    print(json.dumps({"error": str(e)}))