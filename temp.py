from database import *

# Initialize database
init_db()

# Save document
doc_id = save_document(
    "invoice.pdf",
    "invoice",
    "Invoice Number: 101, Amount: 5000",
    "This invoice contains a total amount of 5000."
)

print("Saved Document ID:", doc_id)

# Get all documents
print(get_all_documents())

# Get document by ID
print(get_document_by_id(doc_id))

# Delete document
print(delete_document(doc_id))

from database import (
    init_db,
    save_document,
    get_all_documents,
    get_document_by_id,
    delete_document
)