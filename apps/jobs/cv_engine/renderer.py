import io
import logging

from xhtml2pdf import pisa

from apps.jobs.cv_engine.builder import build_cv_data
from apps.jobs.cv_engine.templates import TEMPLATES

logger = logging.getLogger(__name__)


def render_cv_pdf(job: dict, template_override: str | None = None) -> tuple[bytes, str]:
    data = build_cv_data(job)
    template_type = template_override or data["template_type"]

    template_fn = TEMPLATES.get(template_type, TEMPLATES["modern"])
    html_content = template_fn(data)

    output = io.BytesIO()
    status = pisa.CreatePDF(html_content, dest=output, encoding="utf-8")

    if status.err:
        logger.error(f"CV PDF generation failed with {status.err} errors")
        raise RuntimeError("Failed to generate CV PDF")

    pdf_bytes = output.getvalue()
    output.close()

    safe_company = data["target_company"].replace(" ", "_")[:30] or "Company"
    filename = f"CV_{safe_company}_{template_type}.pdf"

    return pdf_bytes, filename
