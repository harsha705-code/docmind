import streamlit as st
import os
import json
import tempfile
import inspect
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import project modules
import ocr_module
import converter_module
import editor_module
import pdf_tools
import ai_module
import database
import export_module

st.set_page_config(
    page_title="DocuMind | Intelligent Document Processing",
    page_icon="📄",
    layout="wide"
)

# -------------------------------
# HELPER FUNCTIONS
# -------------------------------

def get_function(module, names):
    """Find the first available function from a module."""
    for name in names:
        func = getattr(module, name, None)
        if callable(func):
            return func
    return None


def call_function(func, values):
    """
    Match supplied values to the actual function parameters.
    This helps integrate modules with different parameter names.
    """
    if func is None:
        raise AttributeError("Required function was not found.")

    signature = inspect.signature(func)
    kwargs = {}
    required = []

    aliases = {
        "file": ["file", "uploaded_file", "document", "input_file"],
        "file_path": ["file_path", "path", "image_path", "pdf_path"],
        "file_bytes": ["file_bytes", "data", "content", "image_bytes"],
        "text": ["text", "document_text", "extracted_text", "content"],
        "name": ["name", "document_name", "filename", "file_name"],
        "summary": ["summary", "ai_summary"],
        "structured_data": ["structured_data", "data", "extracted_data"]
    }

    for param_name, param in signature.parameters.items():
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD
        ):
            continue

        matched = False

        for key, possible_names in aliases.items():
            if param_name.lower() in possible_names and key in values:
                kwargs[param_name] = values[key]
                matched = True
                break

        if not matched and param.default is inspect.Parameter.empty:
            required.append(param_name)

    if required:
        if len(required) == 1 and "text" in values:
            return func(values["text"])

        raise TypeError(
            f"Cannot automatically match parameters {required} "
            f"for {func.__module__}.{func.__name__}{signature}"
        )

    return func(**kwargs)


def extract_result_text(result):
    """Convert common OCR output formats into text."""
    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        for key in ("text", "extracted_text", "content", "result"):
            if isinstance(result.get(key), str):
                return result[key]

    if isinstance(result, (list, tuple)):
        return "\n".join(str(item) for item in result)

    return str(result)


def make_pdf(text):
    """Create a PDF download from text."""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from xml.sax.saxutils import escape
    from io import BytesIO

    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()

    story = [
        Paragraph("DocuMind Document Analysis", styles["Title"]),
        Spacer(1, 0.2 * inch)
    ]

    for line in text.splitlines():
        story.append(Paragraph(escape(line) or " ", styles["BodyText"]))
        story.append(Spacer(1, 5))

    document.build(story)
    output.seek(0)
    return output.getvalue()


# -------------------------------
# DATABASE INITIALIZATION
# -------------------------------

try:
    init_db = get_function(database, ["init_db"])
    if init_db:
        init_db()
except Exception as e:
    st.warning(f"Database initialization: {e}")


# -------------------------------
# SIDEBAR
# -------------------------------

st.sidebar.title("📄 DocuMind")
st.sidebar.caption("Intelligent Document Processing System")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Process Document",
        "Document History",
        "About"
    ]
)


# -------------------------------
# DASHBOARD
# -------------------------------

if page == "Dashboard":

    st.title("📄 DocuMind")
    st.subheader("Intelligent Document Processing System")

    st.write(
        "Upload documents, extract information, identify missing fields, "
        "detect inconsistencies and generate AI-powered summaries."
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("AI Analysis", "Enabled")
    col2.metric("OCR Processing", "Enabled")
    col3.metric("Export Options", "3")

    st.divider()

    st.markdown("### What DocuMind can do")

    c1, c2 = st.columns(2)

    with c1:
        st.info("📷 **OCR**\n\nExtract text from scanned documents.")
        st.info("🤖 **AI Analysis**\n\nSummarize and classify documents.")

    with c2:
        st.info("🔍 **Validation**\n\nIdentify missing fields and inconsistencies.")
        st.info("📥 **Export**\n\nDownload processed results.")


# -------------------------------
# PROCESS DOCUMENT
# -------------------------------

elif page == "Process Document":

    st.title("📤 Process Your Document")

    uploaded_file = st.file_uploader(
        "Upload your document",
        type=["pdf", "png", "jpg", "jpeg"]
    )

    if uploaded_file:

        st.success(f"Uploaded: {uploaded_file.name}")

        if st.button("🚀 Process Document", type="primary"):

            file_bytes = uploaded_file.getvalue()

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=os.path.splitext(uploaded_file.name)[1]
            ) as temp:
                temp.write(file_bytes)
                temp_path = temp.name

            try:
                with st.spinner("Extracting document text..."):

                    ocr_func = get_function(
                        ocr_module,
                        ["process_document", "extract_text"]
                    )

                    if not ocr_func:
                        raise AttributeError(
                            "Neither process_document nor extract_text "
                            "exists in ocr_module.py"
                        )

                    ocr_result = call_function(
                        ocr_func,
                        {
                            "file": uploaded_file,
                            "file_path": temp_path,
                            "file_bytes": file_bytes,
                            "name": uploaded_file.name
                        }
                    )

                    extracted_text = extract_result_text(ocr_result)

                if not extracted_text.strip():
                    st.warning("No text was extracted.")
                    st.stop()

                st.session_state["extracted_text"] = extracted_text
                st.session_state["document_name"] = uploaded_file.name

                st.success("Text extraction completed!")

                with st.spinner("Running AI analysis..."):

                    summary_func = get_function(
                        ai_module,
                        ["summarize_document"]
                    )

                    classify_func = get_function(
                        ai_module,
                        ["classify_document"]
                    )

                    structured_func = get_function(
                        ai_module,
                        ["extract_structured_data"]
                    )

                    summary = (
                        call_function(summary_func, {"text": extracted_text})
                        if summary_func else "Summary function unavailable."
                    )

                    classification = (
                        call_function(classify_func, {"text": extracted_text})
                        if classify_func else "Classification unavailable."
                    )

                    structured_data = (
                        call_function(structured_func, {"text": extracted_text})
                        if structured_func else {}
                    )

                st.session_state["summary"] = summary
                st.session_state["classification"] = classification
                st.session_state["structured_data"] = structured_data

                # Validation
                missing_func = get_function(
                    editor_module,
                    ["detect_missing_fields"]
                )

                validation_func = get_function(
                    editor_module,
                    ["validate_document"]
                )

                missing_fields = (
                    call_function(missing_func, {"text": extracted_text})
                    if missing_func else "Validation function unavailable."
                )

                validation = (
                    call_function(validation_func, {"text": extracted_text})
                    if validation_func else "Validation unavailable."
                )

                st.session_state["missing_fields"] = missing_fields
                st.session_state["validation"] = validation

                # Save document to database
                save_func = get_function(
                    database,
                    ["save_document", "save_document_history"]
                )

                if save_func:
                    try:
                        call_function(
                            save_func,
                            {
                                "name": uploaded_file.name,
                                "text": extracted_text,
                                "summary": str(summary),
                                "structured_data": structured_data
                            }
                        )
                    except Exception as db_error:
                        st.warning(f"Database save issue: {db_error}")

                st.success("Document processing completed!")

            except Exception as e:
                st.error(f"Processing error: {e}")

            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    # Display analysis
    if "extracted_text" in st.session_state:

        st.divider()
        st.subheader("📃 Extracted Text")

        st.text_area(
            "Document Content",
            st.session_state["extracted_text"],
            height=220
        )

        st.subheader("🤖 AI Summary")
        st.write(st.session_state.get("summary", ""))

        st.subheader("📌 Document Classification")
        st.write(st.session_state.get("classification", ""))

        st.subheader("🔍 Missing Fields")
        st.write(st.session_state.get("missing_fields", ""))

        st.subheader("⚠️ Document Validation")
        st.write(st.session_state.get("validation", ""))

        st.subheader("📊 Structured Information")
        structured = st.session_state.get("structured_data", {})

        if isinstance(structured, (dict, list)):
            st.json(structured)
        else:
            st.write(structured)

        # -------------------------------
        # EXPORT OPTIONS
        # -------------------------------

        st.divider()
        st.subheader("📥 Download Results")

        text = st.session_state["extracted_text"]
        summary = str(st.session_state.get("summary", ""))
        document_name = st.session_state.get("document_name", "document")

        complete_report = f"""
DOCUMIND - DOCUMENT ANALYSIS

Document: {document_name}

EXTRACTED TEXT:
{text}

AI SUMMARY:
{summary}

CLASSIFICATION:
{st.session_state.get("classification", "")}

MISSING FIELDS:
{st.session_state.get("missing_fields", "")}

VALIDATION:
{st.session_state.get("validation", "")}
"""

        col1, col2, col3 = st.columns(3)

        with col1:
            st.download_button(
                "📄 Download TXT",
                data=complete_report,
                file_name="documind_report.txt",
                mime="text/plain"
            )

        with col2:
            try:
                pdf_data = make_pdf(complete_report)

                st.download_button(
                    "📕 Download PDF",
                    data=pdf_data,
                    file_name="documind_report.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"PDF export error: {e}")

        with col3:
            json_data = {
                "document_name": document_name,
                "extracted_text": text,
                "summary": summary,
                "classification": str(
                    st.session_state.get("classification", "")
                ),
                "missing_fields": str(
                    st.session_state.get("missing_fields", "")
                ),
                "validation": str(
                    st.session_state.get("validation", "")
                ),
                "structured_data": structured
            }

            st.download_button(
                "📊 Download JSON",
                data=json.dumps(json_data, indent=4, default=str),
                file_name="documind_report.json",
                mime="application/json"
            )


# -------------------------------
# DOCUMENT HISTORY
# -------------------------------

elif page == "Document History":

    st.title("📚 Document History")

    history_func = get_function(
        database,
        ["get_all_documents", "get_document_history"]
    )

    if history_func:

        try:
            history = history_func()

            if history:
                if isinstance(history, list):
                    st.dataframe(history, use_container_width=True)
                else:
                    st.write(history)
            else:
                st.info("No processed documents found.")

        except Exception as e:
            st.error(f"Unable to retrieve history: {e}")

    else:
        st.warning("Document history function is not available.")


# -------------------------------
# ABOUT
# -------------------------------

elif page == "About":

    st.title("About DocuMind")

    st.write("""
    DocuMind is an Intelligent Document Processing System.

    It combines:

    - Optical Character Recognition (OCR)
    - Image and PDF conversion
    - AI-powered document analysis
    - Missing field identification
    - Document validation
    - Database management
    - PDF, TXT and JSON exports

    **Developed as a three-member hackathon project.**
    """)

st.sidebar.divider()
st.sidebar.caption("DocuMind | Intelligent Document Processing")