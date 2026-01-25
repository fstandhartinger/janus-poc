from memory_service.services import llm


def test_parse_extracted_memories_filters_invalid_and_truncates():
    content = (
        "LLM output: ["
        "{\"caption\": \"" + "A" * 120 + "\", "
        "\"full_text\": \"" + "B" * 520 + "\"},"
        "{\"caption\": \"\", \"full_text\": \"\"},"
        "\"not-an-object\""
        "]"
    )
    parsed = llm._parse_extracted_memories(content)
    assert len(parsed) == 1
    assert len(parsed[0].caption) <= 100
    assert len(parsed[0].full_text) <= 500


def test_parse_relevant_ids_extracts_strings():
    content = "Result: [\"mem_1\", 123, \"mem_2\"]"
    parsed = llm._parse_relevant_ids(content)
    assert parsed == ["mem_1", "mem_2"]


def test_extract_json_array_handles_invalid():
    assert llm._extract_json_array("no json here") == []
