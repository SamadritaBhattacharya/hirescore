"""
Document parsers for resume, JD, and culture docs.

Design:
- Interface Segregation: DocumentParser protocol defines the contract
- Single Responsibility: each parser handles one file type
- Open/Closed: add new parsers without touching DocumentParserFactory
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Protocol, runtime_checkable

import pdfplumber
from docx import Document

from core.logging import get_logger

logger = get_logger(__name__)


@runtime_checkable
class DocumentParser(Protocol):
    """Protocol defining the contract for all document parsers."""

    def parse(self, content: bytes, filename: str = "") -> str:
        """Extract plain text from document bytes. Returns empty string on failure."""
        ...


class PDFParser:
    """Extracts text from PDF files using pdfplumber."""

    def parse(self, content: bytes, filename: str = "") -> str:
        try:
            text_parts: list[str] = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            result = "\n\n".join(text_parts)
            logger.info(
                "pdf_parsed",
                filename=filename,
                pages=len(text_parts),
                chars=len(result),
            )
            return result
        except Exception as exc:
            logger.error("pdf_parse_failed", filename=filename, error=str(exc))
            return ""


class DOCXParser:
    """Extracts text from DOCX files using python-docx."""

    def parse(self, content: bytes, filename: str = "") -> str:
        try:
            doc = Document(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            result = "\n".join(paragraphs)
            logger.info("docx_parsed", filename=filename, chars=len(result))
            return result
        except Exception as exc:
            logger.error("docx_parse_failed", filename=filename, error=str(exc))
            return ""


class PlainTextParser:
    """Handles plain text — just decode bytes."""

    def parse(self, content: bytes, filename: str = "") -> str:
        try:
            return content.decode("utf-8", errors="replace")
        except Exception as exc:
            logger.error("text_parse_failed", filename=filename, error=str(exc))
            return ""


class DocumentParserFactory:
    """
    Factory that selects the correct parser by file extension.
    Open/Closed: register new parsers without modifying existing code.
    """

    _registry: dict[str, DocumentParser] = {
        ".pdf": PDFParser(),
        ".docx": DOCXParser(),
        ".doc": DOCXParser(),
        ".txt": PlainTextParser(),
        ".md": PlainTextParser(),
    }

    @classmethod
    def get_parser(cls, filename: str) -> DocumentParser:
        ext = Path(filename).suffix.lower()
        parser = cls._registry.get(ext)
        if parser is None:
            logger.warning("unknown_extension", filename=filename, fallback="text")
            return PlainTextParser()
        return parser

    @classmethod
    def parse(cls, content: bytes, filename: str) -> str:
        """Convenience method: get parser and parse in one call."""
        parser = cls.get_parser(filename)
        return parser.parse(content, filename)

    @classmethod
    def register(cls, extension: str, parser: DocumentParser) -> None:
        """Register a custom parser for an extension."""
        cls._registry[extension.lower()] = parser