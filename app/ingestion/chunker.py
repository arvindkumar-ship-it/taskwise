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
    """Bounded source windows; overlap is included in the size budget.

    Prefer separators in the latter part of each window, but hard-slice a
    long paragraph/word when necessary. Preserve source characters instead
    of concatenating an oversized paragraph onto an overlap prefix.
    """
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("Require chunk_size > 0 and 0 <= chunk_overlap < chunk_size")
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            minimum = start + max(chunk_overlap + 1, chunk_size // 2)
            for separator in SEPARATORS:
                boundary = text.rfind(separator, minimum, end)
                if boundary >= minimum:
                    end = boundary + len(separator)
                    break
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - chunk_overlap
    return chunks
