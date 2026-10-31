
import io
import fitz
import pymupdf as fitz

from pdf_tools import (
    merge_pdfs,
    split_pdf,
    rotate_pdf,
    extract_pages,
    remove_blank_pages,
    compress_pdf
)


def create_sample_pdf(include_blank=False):

    doc = fitz.open()

    page = doc.new_page()
    page.insert_text((100, 100), "DocuMind Test Page 1")

    if include_blank:
        doc.new_page()

    page = doc.new_page()
    page.insert_text((100, 100), "DocuMind Test Page 2")

    data = doc.tobytes()
    doc.close()

    return io.BytesIO(data)


# Create sample PDFs
pdf1 = create_sample_pdf()
pdf2 = create_sample_pdf()


# 1. MERGE
merged = merge_pdfs([pdf1, pdf2])
print("1. Merge successful:", len(merged.getvalue()))


# 2. SPLIT
split = split_pdf(merged, [1, 2])
print("2. Split successful:", len(split.getvalue()))


# 3. ROTATE
rotated = rotate_pdf(merged, 1, 90)
print("3. Rotation successful:", len(rotated.getvalue()))


# 4. EXTRACT
extracted = extract_pages(merged, [1, 3])
print("4. Extraction successful:", len(extracted.getvalue()))


# 5. REMOVE BLANK PAGES
blank_pdf = create_sample_pdf(include_blank=True)

cleaned = remove_blank_pages(blank_pdf)

cleaned_doc = fitz.open(
    stream=cleaned.getvalue(),
    filetype="pdf"
)

print("5. Blank page removal successful:",
      cleaned_doc.page_count, "pages")

cleaned_doc.close()


# 6. COMPRESS
compressed = compress_pdf(merged)

print("6. Compression successful:",
      len(compressed.getvalue()), "bytes")


print("\nAll six PDF functions executed successfully!")
