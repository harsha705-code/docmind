
from pathlib import Path
from pypdf import PdfReader


def extract_text(uploaded_file):
    """
    Extract text from uploaded PDF or TXT files.
    Supports Streamlit UploadedFile objects.
    """

    if uploaded_file is None:
        raise ValueError("No document uploaded.")

    file_name = uploaded_file.name.lower()

    try:
        if file_name.endswith(".pdf"):
            pdf_reader = PdfReader(uploaded_file)
            text = ""

            for page in pdf_reader.pages:
                text += page.extract_text() or ""

            if not text.strip():
                raise ValueError(
                    "No text found in PDF. It may require OCR."
                )

            return text

        elif file_name.endswith(".txt"):
            content = uploaded_file.getvalue()
            return content.decode("utf-8-sig")

        else:
            raise ValueError(
                "Unsupported file type. Upload PDF or TXT."
            )

    except Exception as e:
        raise ValueError(f"Text extraction failed: {e}")
