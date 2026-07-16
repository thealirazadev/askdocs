from app.services.chunking import chunk_text


def test_short_input_single_chunk():
    chunks = chunk_text("hello world", chunk_size=1000, overlap=150)
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
    assert chunks[0].char_start == 0
    assert chunks[0].char_end == 11


def test_blank_input_yields_no_chunks():
    assert chunk_text("   \n  ") == []
    assert chunk_text("") == []


def test_overlap_boundaries_are_contiguous():
    text = "a" * 2500
    chunks = chunk_text(text, chunk_size=1000, overlap=150)
    assert len(chunks) == 3
    for i in range(len(chunks) - 1):
        assert chunks[i].char_end - chunks[i + 1].char_start == 150
        assert chunks[i + 1].char_start == chunks[i].char_start + (1000 - 150)
    assert chunks[-1].char_end == len(text)


def test_chunk_indices_are_sequential():
    text = "word " * 1000
    chunks = chunk_text(text)
    assert [c.index for c in chunks] == list(range(len(chunks)))
