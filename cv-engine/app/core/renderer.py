import io
import logging

logger = logging.getLogger(__name__)


def render_pdf(html: str) -> bytes:
    from xhtml2pdf import pisa

    output = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=output)

    if pisa_status.err:
        logger.error(f"PDF generation failed with {pisa_status.err} errors")
        raise ValueError("PDF generation failed")

    pdf_bytes = output.getvalue()

    if _count_pages(pdf_bytes) > 1:
        html = _compress_for_single_page(html, level=1)
        output = io.BytesIO()
        pisa.CreatePDF(html, dest=output)
        pdf_bytes = output.getvalue()

    if _count_pages(pdf_bytes) > 1:
        html = _compress_for_single_page(html, level=2)
        output = io.BytesIO()
        pisa.CreatePDF(html, dest=output)
        pdf_bytes = output.getvalue()

    return pdf_bytes


def _count_pages(pdf_bytes: bytes) -> int:
    count = pdf_bytes.count(b"/Type /Page") - pdf_bytes.count(b"/Type /Pages")
    return max(count, 1)


def _compress_for_single_page(html: str, level: int = 1) -> str:
    if level == 1:
        html = html.replace("font-size: 10pt", "font-size: 9pt")
        html = html.replace("font-size: 11pt", "font-size: 10pt")
        html = html.replace("font-size: 16pt", "font-size: 14pt")
        html = html.replace("font-size: 9.5pt", "font-size: 9pt")
        html = html.replace("margin: 1.2cm 1.5cm", "margin: 1cm 1.3cm")
        html = html.replace("line-height: 1.3", "line-height: 1.2")
        html = html.replace("line-height: 1.4", "line-height: 1.2")
        html = html.replace("line-height: 1.25", "line-height: 1.15")
        html = html.replace("margin-bottom: 6pt", "margin-bottom: 3pt")
        html = html.replace("margin-bottom: 4pt", "margin-bottom: 2pt")
        html = html.replace("margin-bottom: 3pt", "margin-bottom: 2pt")
    elif level == 2:
        html = html.replace("font-size: 9pt", "font-size: 8.5pt")
        html = html.replace("font-size: 10pt", "font-size: 9pt")
        html = html.replace("font-size: 14pt", "font-size: 12pt")
        html = html.replace("margin: 1cm 1.3cm", "margin: 0.8cm 1cm")
        html = html.replace("line-height: 1.2", "line-height: 1.1")
        html = html.replace("line-height: 1.15", "line-height: 1.1")
        html = html.replace("margin-bottom: 3pt", "margin-bottom: 1pt")
        html = html.replace("margin-bottom: 2pt", "margin-bottom: 1pt")
        html = html.replace("letter-spacing: 0.5pt", "letter-spacing: 0.2pt")

    return html
