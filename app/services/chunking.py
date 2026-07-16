"""Fixed-size text chunker with overlap."""

from dataclasses import dataclass

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


@dataclass
class Chunk:
    index: int
    text: str
    char_start: int
    char_end: int


def chunk_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[Chunk]:
    """Split text into fixed-size, overlapping chunks.

    Chunks are contiguous: chunk[i].char_end == chunk[i+1].char_start + overlap for all but the
    last chunk. A blank/whitespace-only text yields no chunks; callers treat that as an empty
    document.
    """
    stripped = text.strip()
    if not stripped:
        return []

    step = chunk_size - overlap
    chunks: list[Chunk] = []
    start = 0
    index = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        piece = text[start:end]
        if piece.strip():
            chunks.append(Chunk(index=index, text=piece, char_start=start, char_end=end))
            index += 1
        if end >= length:
            break
        start += step
    return chunks
