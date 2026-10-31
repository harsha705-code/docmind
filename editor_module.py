"""
editor_module.py

DocuMind - AI-powered Document Scanning and Editing System

Features:
1. Validate document information and detect conflicting values.
2. Detect missing fields in invoices, certificates, forms, and reports.
3. Compare original OCR text with corrected text.
4. Suggest spelling and formatting improvements.

Important:
- Original OCR text is never modified automatically.
- All corrections are suggestions only.
- Uses Python standard-library modules only.
"""

import re
import difflib
from datetime import datetime
from decimal import Decimal, InvalidOperation
from collections import defaultdict


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _clean_text(text):
    """Safely normalize input text."""
    if not isinstance(text, str):
        return ""
    return text.strip()


def _normalize_value(value):
    """Normalize extracted values for comparison."""
    return re.sub(r"\s+", " ", value.strip().lower())


def _extract_labeled_values(text, labels):
    """
    Extract values appearing after specified labels.

    Example:
        Invoice Number: INV-101
        Total Amount: 5000
    """
    results = defaultdict(list)

    for label in labels:
        pattern = (
            r"(?im)^\s*"
            + re.escape(label)
            + r"\s*[:#-]\s*(.+?)\s*$"
        )

        matches = re.findall(pattern, text)

        for value in matches:
            value = value.strip()

            if value:
                results[label.lower()].append(value)

    return dict(results)


def _extract_dates(text):
    """Extract recognizable dates from document text."""

    patterns = [
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
        r"\b\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"
    ]

    dates = []

    for pattern in patterns:
        dates.extend(re.findall(pattern, text, re.IGNORECASE))

    return list(dict.fromkeys(dates))


def _parse_date(value):
    """Convert a recognized date into a standard date object."""

    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%y",
        "%d/%m/%y",
        "%d %B %Y",
        "%B %d, %Y",
        "%B %d %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue

    return None


def _extract_amounts(text, labels):
    """Extract monetary values associated with given labels."""

    results = defaultdict(list)

    for label in labels:
        pattern = (
            r"(?im)^\s*"
            + re.escape(label)
            + r"\s*[:#-]\s*"
            r"(?:₹|Rs\.?|INR|\$|USD)?\s*"
            r"([\d,]+(?:\.\d{1,2})?)"
        )

        matches = re.findall(pattern, text)

        for value in matches:
            try:
                results[label.lower()].append(
                    Decimal(value.replace(",", ""))
                )
            except InvalidOperation:
                continue

    return dict(results)


def _extract_entities(text, document_type):
    """Extract commonly labeled names and identification numbers."""

    labels = [
        "Name",
        "Holder Name",
        "Applicant Name",
        "Student Name",
        "Customer Name",
        "Seller",
        "Buyer",
        "Issued By",
        "Issuing Authority",
        "Company Name",
        "Organization",
        "ID",
        "ID Number",
        "Registration Number",
        "Certificate Number",
        "Invoice Number",
        "GSTIN",
        "PAN",
        "Aadhaar Number"
    ]

    return _extract_labeled_values(text, labels)


def _has_field(text, patterns):
    """Check whether at least one pattern exists in the text."""

    return any(
        re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        for pattern in patterns
    )


# ============================================================
# 1. DOCUMENT VALIDATION
# ============================================================

def validate_document(text, document_type):
    """
    Validate document content.

    Detects:
    - Conflicting dates.
    - Conflicting names.
    - Conflicting identification numbers.
    - Conflicting monetary amounts.
    - Invalid date formats where recognizable.
    - Invoice calculation inconsistencies.

    Args:
        text (str): OCR-extracted document text.
        document_type (str): invoice, certificate, form, or report.

    Returns:
        dict: Structured validation results.
    """

    try:
        text = _clean_text(text)
        document_type = str(document_type or "").lower().strip()

        if not text:
            return {
                "success": False,
                "valid": False,
                "document_type": document_type,
                "errors": ["Document text is empty."],
                "warnings": [],
                "conflicts": [],
                "invoice_checks": {},
                "message": "No document content available for validation."
            }

        errors = []
        warnings = []
        conflicts = []

        # ----------------------------------------------------
        # DATE VALIDATION
        # ----------------------------------------------------

        dates = _extract_dates(text)

        parsed_dates = {}

        for date_string in dates:
            parsed = _parse_date(date_string)

            if parsed:
                parsed_dates[date_string] = parsed
            else:
                warnings.append({
                    "field": "date",
                    "value": date_string,
                    "message": "Date format could not be interpreted reliably."
                })

        unique_dates = set(parsed_dates.values())

        if len(unique_dates) > 1:
            conflicts.append({
                "field": "date",
                "values": dates,
                "message": "Multiple different dates were detected."
            })

        # ----------------------------------------------------
        # NAME AND ID VALIDATION
        # ----------------------------------------------------

        entities = _extract_entities(text, document_type)

        for field, values in entities.items():

            normalized_values = list(
                dict.fromkeys(
                    _normalize_value(value)
                    for value in values
                )
            )

            if len(normalized_values) > 1:
                conflicts.append({
                    "field": field,
                    "values": values,
                    "message": (
                        f"Conflicting values detected for {field}."
                    )
                })

        # ----------------------------------------------------
        # AMOUNT VALIDATION
        # ----------------------------------------------------

        amount_labels = [
            "Subtotal",
            "Tax",
            "GST",
            "Total",
            "Grand Total",
            "Amount",
            "Discount"
        ]

        amounts = _extract_amounts(text, amount_labels)

        for field, values in amounts.items():

            unique_values = set(values)

            if len(unique_values) > 1:
                conflicts.append({
                    "field": field,
                    "values": [str(v) for v in values],
                    "message": (
                        f"Different monetary values found for {field}."
                    )
                })

        # ----------------------------------------------------
        # INVOICE CALCULATION VALIDATION
        # ----------------------------------------------------

        invoice_checks = {}

        if "invoice" in document_type:

            subtotal_values = amounts.get("subtotal", [])
            tax_values = amounts.get("tax", [])
            gst_values = amounts.get("gst", [])
            total_values = (
                amounts.get("grand total", [])
                or amounts.get("total", [])
                or amounts.get("amount", [])
            )
            discount_values = amounts.get("discount", [])

            tax_values = tax_values or gst_values

            if subtotal_values and total_values:

                subtotal = subtotal_values[0]
                total = total_values[0]

                tax = tax_values[0] if tax_values else Decimal("0")
                discount = (
                    discount_values[0]
                    if discount_values
                    else Decimal("0")
                )

                expected_total = subtotal + tax - discount

                difference = abs(expected_total - total)

                calculation_valid = difference <= Decimal("0.01")

                invoice_checks = {
                    "subtotal": str(subtotal),
                    "tax": str(tax),
                    "discount": str(discount),
                    "expected_total": str(expected_total),
                    "actual_total": str(total),
                    "difference": str(difference),
                    "calculation_valid": calculation_valid
                }

                if not calculation_valid:
                    conflicts.append({
                        "field": "invoice_total",
                        "values": {
                            "expected": str(expected_total),
                            "actual": str(total)
                        },
                        "message": (
                            "Invoice total does not match "
                            "subtotal + tax - discount."
                        )
                    })

            else:
                invoice_checks = {
                    "calculation_valid": None,
                    "message": (
                        "Insufficient information to verify "
                        "invoice calculations."
                    )
                }

        # ----------------------------------------------------
        # FINAL VALIDATION RESULT
        # ----------------------------------------------------

        valid = len(errors) == 0 and len(conflicts) == 0

        return {
            "success": True,
            "valid": valid,
            "document_type": document_type,
            "errors": errors,
            "warnings": warnings,
            "conflicts": conflicts,
            "invoice_checks": invoice_checks,
            "extracted_dates": dates,
            "extracted_entities": entities,
            "extracted_amounts": {
                key: [str(value) for value in values]
                for key, values in amounts.items()
            },
            "message": (
                "Document validation completed successfully."
                if valid
                else "Potential document inconsistencies detected."
            )
        }

    except Exception as error:
        return {
            "success": False,
            "valid": False,
            "document_type": document_type,
            "errors": [str(error)],
            "warnings": [],
            "conflicts": [],
            "invoice_checks": {},
            "message": "An error occurred during document validation."
        }


# ============================================================
# 2. MISSING FIELD DETECTION
# ============================================================

def detect_missing_fields(text, document_type):
    """
    Detect missing information based on document type.

    Supported document types:
    - Invoice
    - Certificate
    - Form
    - Report

    Fields are considered present when their corresponding
    labels and non-empty values are detected.

    Returns:
        dict: Missing fields and detected fields.
    """

    try:
        text = _clean_text(text)
        document_type = str(document_type or "").lower().strip()

        if not text:
            return {
                "success": False,
                "document_type": document_type,
                "missing_fields": [],
                "present_fields": [],
                "message": "Document text is empty."
            }

        missing_fields = []
        present_fields = []

        # ----------------------------------------------------
        # INVOICE
        # ----------------------------------------------------

        if "invoice" in document_type:

            field_patterns = {
                "invoice_number": [
                    r"invoice\s*(?:number|no\.?|#)\s*[:#-]\s*\S+"
                ],
                "date": [
                    r"(?:invoice\s*)?date\s*[:#-]\s*\S+"
                ],
                "seller": [
                    r"(?:seller|supplier|vendor|from)\s*[:#-]\s*\S+"
                ],
                "buyer": [
                    r"(?:buyer|customer|bill\s*to|billed\s*to)"
                    r"\s*[:#-]\s*\S+"
                ],
                "subtotal": [
                    r"subtotal\s*[:#-]\s*\S+"
                ],
                "tax": [
                    r"(?:tax|gst|vat)\s*[:#-]\s*\S+"
                ],
                "total": [
                    r"(?:grand\s*total|total\s*amount|total)"
                    r"\s*[:#-]\s*\S+"
                ]
            }

        # ----------------------------------------------------
        # CERTIFICATE
        # ----------------------------------------------------

        elif "certificate" in document_type:

            field_patterns = {
                "holder_name": [
                    r"(?:holder\s*name|name|awarded\s*to|"
                    r"presented\s*to|certifies\s*that)"
                    r"\s*[:#-]?\s*[A-Za-z][A-Za-z .'-]+"
                ],
                "certificate_title": [
                    r"(?:certificate\s*title|title|"
                    r"certificate\s*of)\s*[:#-]?\s*\S+"
                ],
                "issuing_authority": [
                    r"(?:issuing\s*authority|issued\s*by|"
                    r"authorized\s*by|organization|institution)"
                    r"\s*[:#-]\s*\S+"
                ],
                "date": [
                    r"(?:date|issued\s*on|issue\s*date)"
                    r"\s*[:#-]\s*\S+"
                ]
            }

        # ----------------------------------------------------
        # FORM
        # ----------------------------------------------------

        elif "form" in document_type:

            field_patterns = {
                "full_name": [
                    r"(?:full\s*name|name)\s*[:#-]\s*\S+"
                ],
                "contact_information": [
                    r"(?:email|phone|mobile|contact)"
                    r"\s*[:#-]\s*\S+"
                ],
                "address": [
                    r"address\s*[:#-]\s*\S+"
                ],
                "identification_number": [
                    r"(?:id|registration\s*number|"
                    r"application\s*number)\s*[:#-]\s*\S+"
                ],
                "date": [
                    r"(?:date|application\s*date)"
                    r"\s*[:#-]\s*\S+"
                ],
                "signature": [
                    r"signature\s*[:#-]?\s*\S+"
                ]
            }

        # ----------------------------------------------------
        # REPORT
        # ----------------------------------------------------

        elif "report" in document_type:

            field_patterns = {
                "report_title": [
                    r"(?:report\s*title|title|subject)"
                    r"\s*[:#-]\s*\S+"
                ],
                "author": [
                    r"(?:author|prepared\s*by|written\s*by)"
                    r"\s*[:#-]\s*\S+"
                ],
                "date": [
                    r"(?:date|report\s*date)"
                    r"\s*[:#-]\s*\S+"
                ],
                "introduction": [
                    r"\bintroduction\b"
                ],
                "main_content": [
                    r"\b(?:findings|results|analysis|discussion)\b"
                ],
                "conclusion": [
                    r"\bconclusion\b"
                ]
            }

        else:

            return {
                "success": True,
                "document_type": document_type,
                "missing_fields": [],
                "present_fields": [],
                "message": (
                    "Unsupported document type. "
                    "Please specify invoice, certificate, form, or report."
                )
            }

        # ----------------------------------------------------
        # CHECK EACH FIELD
        # ----------------------------------------------------

        for field, patterns in field_patterns.items():

            if _has_field(text, patterns):
                present_fields.append(field)
            else:
                missing_fields.append(field)

        return {
            "success": True,
            "document_type": document_type,
            "missing_fields": missing_fields,
            "present_fields": present_fields,
            "total_missing": len(missing_fields),
            "total_present": len(present_fields),
            "complete": len(missing_fields) == 0,
            "message": (
                "All required fields are present."
                if not missing_fields
                else "Some required fields are missing."
            )
        }

    except Exception as error:
        return {
            "success": False,
            "document_type": document_type,
            "missing_fields": [],
            "present_fields": [],
            "error": str(error),
            "message": "Error while detecting missing fields."
        }


# ============================================================
# 3. TEXT COMPARISON
# ============================================================

def compare_text(original_text, corrected_text):
    """
    Compare original OCR text with corrected text.

    Identifies:
    - Added content.
    - Removed content.
    - Changed content.
    - Unchanged content.

    Original text remains untouched.

    Returns:
        dict: Structured comparison results.
    """

    try:
        original_text = _clean_text(original_text)
        corrected_text = _clean_text(corrected_text)

        if not original_text and not corrected_text:
            return {
                "success": True,
                "added": [],
                "removed": [],
                "changed": [],
                "unchanged": [],
                "message": "Both texts are empty."
            }

        if not original_text:
            return {
                "success": True,
                "added": [corrected_text] if corrected_text else [],
                "removed": [],
                "changed": [],
                "unchanged": [],
                "message": "All corrected content is newly added."
            }

        if not corrected_text:
            return {
                "success": True,
                "added": [],
                "removed": [original_text],
                "changed": [],
                "unchanged": [],
                "message": "All original content was removed."
            }

        # Split text into words for detailed comparison.
        original_words = original_text.split()
        corrected_words = corrected_text.split()

        matcher = difflib.SequenceMatcher(
            None,
            original_words,
            corrected_words,
            autojunk=False
        )

        added = []
        removed = []
        changed = []
        unchanged = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():

            old_content = " ".join(original_words[i1:i2])
            new_content = " ".join(corrected_words[j1:j2])

            if tag == "equal":

                if old_content:
                    unchanged.append(old_content)

            elif tag == "insert":

                added.append(new_content)

            elif tag == "delete":

                removed.append(old_content)

            elif tag == "replace":

                changed.append({
                    "original": old_content,
                    "corrected": new_content
                })

        return {
            "success": True,
            "added": added,
            "removed": removed,
            "changed": changed,
            "unchanged": unchanged,
            "statistics": {
                "original_word_count": len(original_words),
                "corrected_word_count": len(corrected_words),
                "added_segments": len(added),
                "removed_segments": len(removed),
                "changed_segments": len(changed),
                "unchanged_segments": len(unchanged)
            },
            "message": "Text comparison completed successfully."
        }

    except Exception as error:
        return {
            "success": False,
            "added": [],
            "removed": [],
            "changed": [],
            "unchanged": [],
            "error": str(error),
            "message": "An error occurred during text comparison."
        }


# ============================================================
# 4. CORRECTION SUGGESTIONS
# ============================================================

def suggest_corrections(text):
    """
    Suggest spelling and formatting improvements.

    Important:
    - Does not modify original OCR text.
    - Does not automatically apply corrections.
    - Provides suggested changes for user review.

    Uses a small built-in dictionary of common OCR mistakes.
    For comprehensive spelling detection, an external spelling
    library can be integrated separately.

    Returns:
        dict: Original text and suggested corrections.
    """

    try:
        text = _clean_text(text)

        if not text:
            return {
                "success": False,
                "original_text": "",
                "suggestions": [],
                "message": "No text provided."
            }

        suggestions = []

        # ----------------------------------------------------
        # COMMON OCR SPELLING ERRORS
        # ----------------------------------------------------

        common_ocr_errors = {
            "reciept": "receipt",
            "adress": "address",
            "addres": "address",
            "recieved": "received",
            "seperate": "separate",
            "occured": "occurred",
            "definately": "definitely",
            "accomodation": "accommodation",
            "goverment": "government",
            "bussiness": "business",
            "ammount": "amount",
            "invoce": "invoice",
            "certifcate": "certificate",
            "authourity": "authority",
            "contcat": "contact",
            "custmer": "customer",
            "suplier": "supplier",
            "quanity": "quantity",
            "descripton": "description",
            "statment": "statement"
        }

        # ----------------------------------------------------
        # SPELLING SUGGESTIONS
        # ----------------------------------------------------

        for incorrect, correct in common_ocr_errors.items():

            pattern = r"\b" + re.escape(incorrect) + r"\b"

            matches = list(
                re.finditer(pattern, text, re.IGNORECASE)
            )

            for match in matches:

                original_word = match.group()

                suggestions.append({
                    "type": "spelling",
                    "original": original_word,
                    "suggestion": correct,
                    "position": match.start(),
                    "message": (
                        f"Possible spelling correction: "
                        f"{original_word} → {correct}"
                    ),
                    "applied": False
                })

        # ----------------------------------------------------
        # FORMATTING SUGGESTIONS
        # ----------------------------------------------------

        # Multiple consecutive spaces.
        for match in re.finditer(r" {2,}", text):

            suggestions.append({
                "type": "formatting",
                "original": match.group(),
                "suggestion": " ",
                "position": match.start(),
                "message": "Multiple spaces detected.",
                "applied": False
            })

        # Missing space after punctuation.
        for match in re.finditer(r"(?<=[,.!?;:])(?=[A-Za-z0-9])", text):

            suggestions.append({
                "type": "formatting",
                "original": "",
                "suggestion": " ",
                "position": match.start(),
                "message": (
                    "Consider adding a space after punctuation."
                ),
                "applied": False
            })

        # Leading and trailing whitespace.
        if text != text.strip():

            suggestions.append({
                "type": "formatting",
                "original": text,
                "suggestion": text.strip(),
                "position": 0,
                "message": "Remove unnecessary leading or trailing spaces.",
                "applied": False
            })

        # Multiple blank lines.
        for match in re.finditer(r"\n{3,}", text):

            suggestions.append({
                "type": "formatting",
                "original": match.group(),
                "suggestion": "\n\n",
                "position": match.start(),
                "message": "Reduce excessive blank lines.",
                "applied": False
            })

        # ----------------------------------------------------
        # CAPITALIZATION SUGGESTIONS
        # ----------------------------------------------------

        for match in re.finditer(r"(?m)^\s*([a-z])", text):

            original_char = match.group(1)

            suggestions.append({
                "type": "capitalization",
                "original": original_char,
                "suggestion": original_char.upper(),
                "position": match.start(1),
                "message": "Consider capitalizing the beginning of the line.",
                "applied": False
            })

        # ----------------------------------------------------
        # FINAL RESULT
        # ----------------------------------------------------

        return {
            "success": True,
            "original_text": text,
            "suggestions": suggestions,
            "total_suggestions": len(suggestions),
            "spelling_suggestions": sum(
                1 for item in suggestions
                if item["type"] == "spelling"
            ),
            "formatting_suggestions": sum(
                1 for item in suggestions
                if item["type"] == "formatting"
            ),
            "capitalization_suggestions": sum(
                1 for item in suggestions
                if item["type"] == "capitalization"
            ),
            "message": (
                "Correction suggestions generated successfully. "
                "Original OCR text has not been modified."
            )
        }

    except Exception as error:
        return {
            "success": False,
            "original_text": text if isinstance(text, str) else "",
            "suggestions": [],
            "error": str(error),
            "message": "An error occurred while generating suggestions."
        }


# ============================================================
# OPTIONAL: BASIC MODULE TESTING
# ============================================================

if __name__ == "__main__":

    sample_invoice = """
    Invoice Number: INV-101
    Date: 15-10-2026
    Seller: ABC Technologies
    Buyer: XYZ Solutions

    Subtotal: 10000
    Tax: 1800
    Total: 11800
    """

    print("\n========== DOCUMENT VALIDATION ==========")
    print(validate_document(sample_invoice, "invoice"))

    print("\n========== MISSING FIELD DETECTION ==========")
    print(detect_missing_fields(sample_invoice, "invoice"))

    print("\n========== TEXT COMPARISON ==========")
    original = "Invoice Number: INV-101 Total: 10000"
    corrected = "Invoice Number: INV-101 Total: 11800"

    print(compare_text(original, corrected))

    print("\n========== CORRECTION SUGGESTIONS ==========")
    ocr_text = "Invoce Number: 101\nAdress: Delhi"

    print(suggest_corrections(ocr_text))