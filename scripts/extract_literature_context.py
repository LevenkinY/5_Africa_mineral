from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
LIT_DIR = ROOT / "literatures"
PROPOSAL_DIR = ROOT / "ResearchProposal"
OUT = ROOT / "outputs" / "literature_context.json"


def read_pdf(path: Path, max_pages: int = 4, max_chars: int = 9000) -> dict:
    reader = PdfReader(str(path))
    metadata = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
    chunks: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            chunks.append(page.extract_text() or "")
        except Exception as exc:
            chunks.append(f"[extract_error: {exc}]")
    text = "\n".join(chunks)
    return {
        "metadata": metadata,
        "pages": len(reader.pages),
        "text": text[:max_chars],
    }


def read_docx(path: Path, max_chars: int = 12000) -> dict:
    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return {"paragraphs": len(paragraphs), "text": "\n".join(paragraphs)[:max_chars]}


def main() -> None:
    proposals = {}
    for path in sorted(PROPOSAL_DIR.iterdir()):
        if path.suffix.lower() == ".docx":
            proposals[path.name] = read_docx(path, max_chars=20000)
        elif path.suffix.lower() == ".pdf":
            proposals[path.name] = read_pdf(path, max_pages=8, max_chars=20000)

    literature = {}
    for path in sorted(LIT_DIR.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".pdf":
            literature[path.name] = read_pdf(path, max_pages=4, max_chars=12000)
        elif path.suffix.lower() == ".docx":
            literature[path.name] = read_docx(path, max_chars=12000)
        else:
            literature[path.name] = {
                "metadata": {},
                "text": path.read_text(errors="ignore")[:2000],
            }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"proposals": proposals, "literature": literature}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(OUT)


if __name__ == "__main__":
    main()
