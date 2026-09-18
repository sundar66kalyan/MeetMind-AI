from pathlib import Path
import hashlib

from backend.app.services.document_service import (
    extract_pdf_text,
    chunk_document_pages
)
from backend.app.services.vector_service import add_documents


DOCUMENTS_DIR = Path("data") / "documents"


def create_document_id(file_path: str) -> str:
    """
    Create a stable document ID from the PDF filename.
    """

    filename = Path(file_path).name

    return hashlib.sha256(
        filename.encode("utf-8")
    ).hexdigest()[:16]


def process_uploaded_pdf(
    file_path: str,
    document_type: str = "resume"
) -> dict:
    """
    Process an uploaded PDF.

    Steps:
    1. Validate the PDF.
    2. Extract text.
    3. Split text into chunks.
    4. Attach filename to every chunk.
    5. Store chunks using a document-specific ID.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {file_path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            "Only PDF files are supported."
        )

    pages = extract_pdf_text(
        file_path=str(path)
    )

    if not pages:
        raise ValueError(
            "No readable text was found in the PDF."
        )

    chunks = chunk_document_pages(
        pages=pages
    )

    if not chunks:
        raise ValueError(
            "No document chunks were created."
        )

    document_id = create_document_id(
        file_path=str(path)
    )

    # Store the original PDF filename with every chunk.
    for chunk in chunks:
        chunk["filename"] = path.name

    add_documents(
        chunks=chunks,
        document_id=document_id,
        filename=path.name,
        document_type=document_type
    )

    return {
        "filename": path.name,
        "document_id": document_id,
        "pages": len(pages),
        "chunks": len(chunks),
        "status": "indexed"
    }