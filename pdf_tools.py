
"""
pdf_tools.py

DocuMind - PDF Processing Module
Member 2

Features:
1. Merge multiple PDF files.
2. Split selected PDF pages.
3. Rotate a selected PDF page.
4. Extract specified PDF pages.
5. Detect and remove blank pages.
6. Compress PDF files.

Libraries:
    pypdf
    PyMuPDF (fitz)

Important:
- Supports Streamlit UploadedFile objects.
- Supports BytesIO, binary file objects, bytes, and file paths.
- Page numbers start from 1.
- Original PDF files are never modified.
- Every successful function returns BytesIO.
"""

import io
import os

import pymupdf as fitz
from pypdf import PdfReader, PdfWriter


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _read_pdf_bytes(file):
    """Read PDF data without modifying the original file."""

    if file is None:
        raise ValueError("No PDF file was provided.")

    if isinstance(file, bytes):
        data = file

    elif isinstance(file, bytearray):
        data = bytes(file)

    elif isinstance(file, (str, os.PathLike)):
        path = os.fspath(file)

        if not os.path.isfile(path):
            raise ValueError(f"PDF file not found: {path}")

        with open(path, "rb") as pdf_file:
            data = pdf_file.read()

    elif hasattr(file, "getvalue"):
        data = file.getvalue()

    elif hasattr(file, "read"):
        position = None

        try:
            position = file.tell()
        except (AttributeError, OSError):
            pass

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            data = file.read()

        finally:
            if position is not None:
                try:
                    file.seek(position)
                except (AttributeError, OSError):
                    pass

    else:
        raise TypeError(
            "Unsupported input. Provide a PDF file, bytes, "
            "file path, or file-like object."
        )

    if not isinstance(data, bytes):
        data = bytes(data)

    if not data:
        raise ValueError("The PDF file is empty.")

    if not data.startswith(b"%PDF-"):
        raise ValueError("Invalid PDF file. PDF header not found.")

    return data


def _get_pdf_reader(file):
    """Create and validate a PDF reader."""

    data = _read_pdf_bytes(file)

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)

        if reader.is_encrypted:
            raise ValueError(
                "Encrypted PDFs are not supported. "
                "Please upload an unlocked PDF."
            )

        if len(reader.pages) == 0:
            raise ValueError("The PDF contains no pages.")

        return reader, data

    except ValueError:
        raise

    except Exception as error:
        raise ValueError(
            f"Unable to read PDF. It may be corrupted: {error}"
        ) from error


def _get_page_numbers(pages, total_pages):
    """Validate page numbers. Page numbering starts from 1."""

    if pages is None:
        raise ValueError("Please provide page numbers.")

    if isinstance(pages, int) and not isinstance(pages, bool):
        pages = [pages]

    elif isinstance(pages, (str, bytes)):
        raise ValueError("Page numbers must be integers.")

    try:
        pages = list(pages)
    except TypeError as error:
        raise ValueError(
            "Provide page numbers as an integer or list."
        ) from error

    if not pages:
        raise ValueError("No pages were selected.")

    validated = []

    for page in pages:

        if isinstance(page, bool) or not isinstance(page, int):
            raise ValueError(
                f"Invalid page number: {page}. Use integers only."
            )

        if page < 1 or page > total_pages:
            raise ValueError(
                f"Page {page} does not exist. "
                f"This PDF contains {total_pages} pages."
            )

        validated.append(page)

    return validated


def _create_output(writer):
    """Generate an in-memory PDF."""

    output = io.BytesIO()

    try:
        writer.write(output)
        output.seek(0)
        return output

    except Exception as error:
        output.close()
        raise ValueError(
            f"Unable to generate PDF: {error}"
        ) from error


# ============================================================
# 1. MERGE PDF FILES
# ============================================================

def merge_pdfs(files):
    """
    Merge multiple PDF files into one PDF.

    Args:
        files: List of PDF files.

    Returns:
        BytesIO: Merged PDF.
    """

    if files is None:
        raise ValueError("Please provide PDF files.")

    if isinstance(files, (str, bytes, bytearray, os.PathLike)):
        raise ValueError("Provide multiple PDF files as a collection.")

    try:
        files = list(files)
    except TypeError as error:
        raise ValueError(
            "PDF files must be provided as a collection."
        ) from error

    if len(files) < 2:
        raise ValueError(
            "At least two PDF files are required."
        )

    writer = PdfWriter()

    try:
        for index, file in enumerate(files, start=1):

            try:
                reader, _ = _get_pdf_reader(file)

                for page in reader.pages:
                    writer.add_page(page)

            except Exception as error:
                raise ValueError(
                    f"Error processing PDF {index}: {error}"
                ) from error

        return _create_output(writer)

    finally:
        writer.close()


# ============================================================
# 2. SPLIT PDF
# ============================================================

def split_pdf(file, pages):
    """
    Extract selected pages from a PDF.

    Args:
        file: Input PDF.
        pages: Selected page numbers (1-based).

    Returns:
        BytesIO: PDF containing selected pages.
    """

    return extract_pages(file, pages)


# ============================================================
# 3. ROTATE PDF PAGE
# ============================================================

def rotate_pdf(file, page_number, angle):
    """
    Rotate one selected page.

    Supported angles: 90, 180, 270 degrees clockwise.

    Args:
        file: Input PDF.
        page_number: Page number (1-based).
        angle: Rotation angle.

    Returns:
        BytesIO: Rotated PDF.
    """

    reader, _ = _get_pdf_reader(file)

    total_pages = len(reader.pages)

    validated = _get_page_numbers(
        page_number,
        total_pages
    )

    if len(validated) != 1:
        raise ValueError("Only one page can be rotated at a time.")

    if isinstance(angle, bool) or not isinstance(angle, int):
        raise ValueError("Rotation angle must be an integer.")

    if angle not in (90, 180, 270):
        raise ValueError(
            "Supported rotation angles are 90, 180, and 270."
        )

    writer = PdfWriter()

    try:
        for index, page in enumerate(reader.pages):

            if index == page_number - 1:
                page.rotate(angle)

            writer.add_page(page)

        return _create_output(writer)

    finally:
        writer.close()


# ============================================================
# 4. EXTRACT PDF PAGES
# ============================================================

def extract_pages(file, pages):
    """
    Extract specified pages into a new PDF.

    Args:
        file: Input PDF.
        pages: Page numbers to extract (1-based).

    Returns:
        BytesIO: Extracted PDF.
    """

    reader, _ = _get_pdf_reader(file)

    selected_pages = _get_page_numbers(
        pages,
        len(reader.pages)
    )

    writer = PdfWriter()

    try:
        for page_number in selected_pages:

            page = reader.pages[page_number - 1]
            writer.add_page(page)

        return _create_output(writer)

    finally:
        writer.close()


# ============================================================
# 5. REMOVE BLANK PAGES
# ============================================================

def _is_blank_page(page):
    """
    Detect blank pages using PyMuPDF.

    A page is considered blank when it has:
    - No text.
    - No images.
    - No vector drawings.
    - No annotations.
    - No form widgets.

    Pages are preserved if detection encounters an error.
    """

    try:
        # Check text.
        if page.get_text("text").strip():
            return False

        # Check images.
        if page.get_images(full=True):
            return False

        # Check vector drawings.
        if page.get_drawings():
            return False

        # Check annotations.
        annotations = page.annots()

        if annotations is not None:
            if any(True for _ in annotations):
                return False

        # Check form widgets.
        widgets = page.widgets()

        if widgets is not None:
            if any(True for _ in widgets):
                return False

        return True

    except Exception:
        return False


def remove_blank_pages(file):
    """
    Remove blank pages from a PDF.

    Pages containing text, images, drawings, annotations,
    or form widgets are preserved.

    Returns:
        BytesIO: PDF without detected blank pages.
    """

    data = _read_pdf_bytes(file)

    document = None
    output_document = None

    try:
        document = fitz.open(
            stream=data,
            filetype="pdf"
        )

        if document.is_encrypted:
            raise ValueError(
                "Encrypted PDFs are not supported."
            )

        if document.page_count == 0:
            raise ValueError("The PDF contains no pages.")

        pages_to_keep = []

        for index in range(document.page_count):

            page = document.load_page(index)

            if not _is_blank_page(page):
                pages_to_keep.append(index)

        if not pages_to_keep:
            raise ValueError(
                "All pages appear blank. "
                "No output PDF was generated."
            )

        output_document = fitz.open()

        for index in pages_to_keep:

            output_document.insert_pdf(
                document,
                from_page=index,
                to_page=index
            )

        result = output_document.tobytes(
            garbage=3,
            deflate=True
        )

        output = io.BytesIO(result)
        output.seek(0)

        return output

    except ValueError:
        raise

    except Exception as error:
        raise ValueError(
            f"Unable to remove blank pages: {error}"
        ) from error

    finally:
        if output_document is not None:
            output_document.close()

        if document is not None:
            document.close()


# ============================================================
# 6. COMPRESS PDF
# ============================================================

def compress_pdf(file):
    """
    Compress a PDF using PyMuPDF.

    Features:
    - Removes unused PDF objects.
    - Compresses PDF streams.
    - Compresses image streams where possible.
    - Compresses font streams where possible.
    - Cleans PDF structures.

    Original text and vector content are not intentionally
    rasterized.

    Returns:
        BytesIO: Compressed PDF.
    """

    data = _read_pdf_bytes(file)

    document = None

    try:
        document = fitz.open(
            stream=data,
            filetype="pdf"
        )

        if document.is_encrypted:
            raise ValueError(
                "Encrypted PDFs are not supported."
            )

        if document.page_count == 0:
            raise ValueError("The PDF contains no pages.")

        compressed_bytes = document.tobytes(
            garbage=4,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            clean=True
        )

        if not compressed_bytes:
            raise ValueError(
                "Compression produced an empty PDF."
            )

        output = io.BytesIO(compressed_bytes)
        output.seek(0)

        return output

    except ValueError:
        raise

    except Exception as error:
        raise ValueError(
            f"Unable to compress PDF: {error}"
        ) from error

    finally:
        if document is not None:
            document.close()


# ============================================================
# MODULE TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 55)
    print("DocuMind - PDF Processing Module")
    print("=" * 55)

    print("\nAvailable PDF functions:")

    print("1. merge_pdfs(files)")
    print("2. split_pdf(file, pages)")
    print("3. rotate_pdf(file, page_number, angle)")
    print("4. extract_pages(file, pages)")
    print("5. remove_blank_pages(file)")
    print("6. compress_pdf(file)")

    print("\nPDF tools module loaded successfully.")

    print("\nPage numbering starts from 1.")
    print("All functions return BytesIO objects.")
