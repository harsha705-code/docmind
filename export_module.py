
import os
import json
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib.enums import TA_CENTER


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
EXPORT_DIR = BASE_DIR / "exports"


def create_export_folder():
    """Create exports folder if it does not exist."""
    try:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        return True

    except OSError as e:
        print(f"Error creating export folder: {e}")
        return False


def generate_filename(document_name, extension):
    """Generate a safe and unique export filename."""

    try:
        name = Path(document_name).stem
        name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        return f"{name}_{timestamp}.{extension}"

    except Exception as e:
        raise ValueError(f"Filename generation failed: {e}")


# ==========================================
# 1. EXPORT EXTRACTED TEXT AS TXT
# ==========================================

def export_extracted_text(document_name, extracted_text):
    """
    Export extracted document text as TXT.
    Returns generated file path or None.
    """

    try:
        if not isinstance(extracted_text, str):
            raise ValueError("Extracted text must be a string.")

        if not create_export_folder():
            return None

        filename = generate_filename(document_name, "txt")
        file_path = EXPORT_DIR / filename

        with open(file_path, "w", encoding="utf-8") as file:
            file.write("DOCUMIND - EXTRACTED DOCUMENT TEXT\n")
            file.write("=" * 50 + "\n\n")
            file.write(f"Document Name: {document_name}\n")
            file.write(
                f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
            file.write(extracted_text)

        return str(file_path)

    except (OSError, ValueError, TypeError) as e:
        print(f"Extracted text export error: {e}")
        return None


# ==========================================
# 2. EXPORT AI SUMMARY AS TXT
# ==========================================

def export_summary_txt(document_name, ai_summary):
    """
    Export AI-generated document summary as TXT.
    Returns generated file path or None.
    """

    try:
        if not isinstance(ai_summary, str):
            raise ValueError("AI summary must be a string.")

        if not create_export_folder():
            return None

        filename = generate_filename(document_name, "txt")
        file_path = EXPORT_DIR / filename

        with open(file_path, "w", encoding="utf-8") as file:
            file.write("DOCUMIND - AI DOCUMENT SUMMARY\n")
            file.write("=" * 50 + "\n\n")
            file.write(f"Document Name: {document_name}\n")
            file.write(
                f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
            file.write(ai_summary)

        return str(file_path)

    except (OSError, ValueError, TypeError) as e:
        print(f"Summary export error: {e}")
        return None


# ==========================================
# 3. EXPORT DOCUMENT ANALYSIS AS PDF
# ==========================================

def export_analysis_pdf(
    document_name,
    extracted_text,
    ai_summary,
    structured_data
):
    """
    Export complete document analysis as PDF.
    Includes extracted text, AI summary and structured data.
    Returns generated PDF path or None.
    """

    try:
        if not isinstance(extracted_text, str):
            raise ValueError("Extracted text must be a string.")

        if not isinstance(ai_summary, str):
            raise ValueError("AI summary must be a string.")

        if not isinstance(structured_data, dict):
            raise ValueError("Structured data must be a dictionary.")

        if not create_export_folder():
            return None

        filename = generate_filename(document_name, "pdf")
        file_path = EXPORT_DIR / filename

        pdf = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=20,
            textColor=colors.HexColor("#1F4E79"),
            alignment=TA_CENTER,
            spaceAfter=20
        )

        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#2874A6"),
            spaceBefore=15,
            spaceAfter=8
        )

        body_style = ParagraphStyle(
            "CustomBody",
            parent=styles["BodyText"],
            fontSize=9,
            leading=14,
            spaceAfter=8,
            wordWrap="CJK"
        )

        story = []

        # PDF Title
        story.append(
            Paragraph("DOCUMIND DOCUMENT ANALYSIS REPORT", title_style)
        )

        story.append(
            Paragraph(
                f"<b>Document Name:</b> {document_name}",
                body_style
            )
        )

        story.append(
            Paragraph(
                f"<b>Export Date:</b> "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                body_style
            )
        )

        story.append(Spacer(1, 15))

        # AI Summary
        story.append(
            Paragraph("1. AI Document Summary", heading_style)
        )

        safe_summary = (
            ai_summary.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )

        story.append(Paragraph(safe_summary, body_style))

        # Structured Data
        story.append(
            Paragraph("2. Structured Document Data", heading_style)
        )

        table_data = [["Field", "Value"]]

        for key, value in structured_data.items():
            table_data.append([
                str(key),
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else str(value)
            ])

        if len(table_data) == 1:
            table_data.append(["No structured data", "Available"])

        table = Table(
            table_data,
            colWidths=[150, 320],
            repeatRows=1
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))

        story.append(table)

        # Extracted Text
        story.append(
            Paragraph("3. Extracted Document Text", heading_style)
        )

        safe_text = (
            extracted_text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )

        story.append(Paragraph(safe_text, body_style))

        pdf.build(story)

        return str(file_path)

    except (OSError, ValueError, TypeError) as e:
        print(f"PDF export error: {e}")
        return None

    except Exception as e:
        print(f"Unexpected PDF generation error: {e}")
        return None


# ==========================================
# 4. EXPORT STRUCTURED DATA AS JSON
# ==========================================

def export_structured_json(document_name, structured_data):
    """
    Export structured document data as JSON.
    Returns generated JSON path or None.
    """

    try:
        if not isinstance(structured_data, dict):
            raise ValueError("Structured data must be a dictionary.")

        if not create_export_folder():
            return None

        filename = generate_filename(document_name, "json")
        file_path = EXPORT_DIR / filename

        export_data = {
            "document_name": document_name,
            "export_timestamp": datetime.now().isoformat(),
            "structured_data": structured_data
        }

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(
                export_data,
                file,
                indent=4,
                ensure_ascii=False
            )

        return str(file_path)

    except (OSError, ValueError, TypeError) as e:
        print(f"JSON export error: {e}")
        return None


# ==========================================
# MAIN TESTING
# ==========================================

if __name__ == "__main__":

    document_name = "invoice.pdf"

    extracted_text = """
    Invoice Number: 101
    Customer: ABC Company
    Amount: 5000
    """

    ai_summary = """
    This invoice belongs to ABC Company.
    Invoice number is 101.
    Total amount is 5000.
    """

    structured_data = {
        "invoice_number": 101,
        "customer": "ABC Company",
        "amount": 5000,
        "currency": "INR"
    }

    print("\nTesting DocuMind Export Module...\n")

    text_path = export_extracted_text(
        document_name,
        extracted_text
    )

    summary_path = export_summary_txt(
        document_name,
        ai_summary
    )

    pdf_path = export_analysis_pdf(
        document_name,
        extracted_text,
        ai_summary,
        structured_data
    )

    json_path = export_structured_json(
        document_name,
        structured_data
    )

    print("Extracted Text:", text_path)
    print("AI Summary:", summary_path)
    print("PDF Report:", pdf_path)
    print("JSON Data:", json_path)

    print("\nExport testing completed!")
