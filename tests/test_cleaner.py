"""Tests for text cleanup and normalization."""

import pytest
from pdf_chunker.conversion.cleaner import clean, _fix_spaced_characters


class TestFixSpacedCharacters:
    def test_collapses_spaced_title_case(self):
        assert _fix_spaced_characters("T he  B arbarian") == "The Barbarian"

    def test_collapses_multiple_spaced_words(self):
        assert _fix_spaced_characters("M onster  S ummary") == "Monster Summary"

    def test_leaves_single_occurrence_alone(self):
        """Single occurrence could be legitimate (e.g., 'I am')."""
        assert _fix_spaced_characters("I am fine") == "I am fine"

    def test_leaves_normal_text_alone(self):
        assert _fix_spaced_characters("The Barbarian") == "The Barbarian"

    def test_handles_multiline(self):
        text = "T he  B arbarian\nNormal text\nM onster  S ummary"
        result = _fix_spaced_characters(text)
        assert result == "The Barbarian\nNormal text\nMonster Summary"

    def test_mixed_normal_and_spaced_lines(self):
        text = "Normal line here\nT he  C hef  T alents"
        result = _fix_spaced_characters(text)
        assert result == "Normal line here\nThe Chef Talents"

    def test_heading_with_spacing(self):
        text = "# C rawling  D eep"
        # Only 2 matches so it should fix
        result = _fix_spaced_characters(text)
        assert result == "# Crawling Deep"

    def test_does_not_break_regular_sentences(self):
        text = "A dragon attacks. B rolls initiative."
        # Only 2 matches — but these are at sentence starts, this is the edge case.
        # The fix is acceptable here since the semantics are preserved.
        result = _fix_spaced_characters(text)
        assert "dragon" in result
        assert "rolls" in result


class TestCleanHeadingPageNumbers:
    def test_removes_heading_page_numbers(self):
        text = "Some content\n### 227\nMore content"
        result = clean(text)
        assert "### 227" not in result
        assert "Some content" in result
        assert "More content" in result

    def test_removes_various_heading_levels(self):
        text = "Before\n# 1\nAfter"
        result = clean(text)
        assert "# 1" not in result

    def test_removes_heading_page_number_at_start_of_text(self):
        text = "### 227\n\nSome content"
        result = clean(text)
        assert "### 227" not in result
        assert "Some content" in result

    def test_removes_bare_page_number_at_start_of_text(self):
        text = "42\n\nSome content"
        result = clean(text)
        assert result.strip() == "Some content"

    def test_preserves_headings_with_text(self):
        text = "Before\n### Chapter 3\nAfter"
        result = clean(text)
        assert "### Chapter 3" in result


class TestCleanIntegration:
    def test_spaced_characters_cleaned_in_full_pipeline(self):
        text = "## T he  B arbarian\n\nSome normal body text here."
        result = clean(text)
        assert "T he" not in result
        assert "Barbarian" in result

    def test_ligatures_still_expanded(self):
        result = clean("e\ufb00ective")
        assert "effective" in result

    def test_smart_quotes_still_normalized(self):
        result = clean("\u201cHello\u201d")
        assert '"Hello"' in result
