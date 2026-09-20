"""A small, dependency-free text splitter.

Splits on the largest available separator first (paragraph, then line, then
sentence, then word) and packs pieces up to `chunk_size`, carrying
`chunk_overlap` characters of context into the next chunk. This is a
simplified reimplementation of the common "recursive character splitter"
pattern — enough for grounding RAG answers without pulling in a separate
text-splitting package.
"""

SEPARATORS = ["\n\n", "\n", ". ", " "]


def _split(text: str, separators: list[str]) -> list[str]:
    if not separators:
        return list(text)
    sep, rest = separators[0], separators[1:]
    if sep not in text:
        return _split(text, rest)
    return [piece for piece in text.split(sep) if piece]


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []

    pieces = _split(text, SEPARATORS)
    chunks: list[str] = []
    current = ""

    for piece in pieces:
        candidate = f"{current} {piece}".strip() if current else piece
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            # carry the tail of the previous chunk forward for continuity
            current = current[-chunk_overlap:] + " " + piece
        else:
            # a single piece longer than chunk_size — hard-slice it
            for i in range(0, len(piece), chunk_size):
                chunks.append(piece[i : i + chunk_size])
            current = ""

    if current:
        chunks.append(current)

    return chunks
