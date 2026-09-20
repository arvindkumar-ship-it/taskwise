"""Extracts plain text from an uploaded file.

Deliberately hand-rolled instead of pulling in LangChain's document loaders:
fewer transitive dependencies, and each branch is easy to verify by reading it.
"""

from pathlib import Path

import docx2txt
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def load_text_from_file(file_path: str, original_filename: str) -> str:
    ext = Path(original_filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if ext == ".pdf":
        reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages).strip()

    if ext == ".docx":
        return docx2txt.process(file_path).strip()

    # .txt / .md
    return Path(file_path).read_text(encoding="utf-8", errors="ignore").strip()
