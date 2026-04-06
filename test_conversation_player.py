"""
test_conversation_player.py
============================
Unit tests for the conversation parser in conversation_player.py.
Run with:  python3 -m pytest test_conversation_player.py -v
"""

import pytest
from pathlib import Path
from conversation_player import (
    Conversation,
    Speaker,
    build_output_filename,
    parse_conversations,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SINGLE_CONVERSATION = """
Conversation 1

English Speaker
English: Good morning! How are you today?
Tamil: காலை வணக்கம்! நீங்கள் எப்படி இருக்கிறீர்கள்?
Pronunciation: Kaalai vanakkam! Neengal eppadi irukkireergal?

LOTE Speaker
English: I am fine, thank you. And you?
Tamil: நான் நலமாக இருக்கிறேன், நன்றி. நீங்களோ?
Pronunciation: Naan nalamaga irukkiren, nandri. Neengalo?
"""

TWO_CONVERSATIONS = """
Conversation 1

English Speaker
English: Where is the nearest hospital?
Tamil: மிகவும் அருகில் உள்ள மருத்துவமனை எங்கே உள்ளது?
Pronunciation: Migavum arugil ulla maruththuvamanaai enge ulladu?

LOTE Speaker
English: It is about two kilometres from here.
Tamil: இங்கிருந்து சுமார் இரண்டு கிலோமீட்டர் தொலைவில் உள்ளது.
Pronunciation: Ingirundhu sumaar irandu kilomeettar thollaivil ulladu.

---

Conversation 2

English Speaker
English: I need to make an appointment with the doctor.
Tamil: எனக்கு மருத்துவரிடம் ஒரு சந்திப்பு வேண்டும்.
Pronunciation: Enakku maruththuvariddam oru sandhippu vendum.

LOTE Speaker
English: Of course. What day would suit you?
Tamil: நிச்சயமாக. உங்களுக்கு எந்த நாள் வசதியாக இருக்கும்?
Pronunciation: Nichchayamaga. Ungalukkku enda naal vasadhiyaga irukkum?
"""

MISSING_SECTIONS = """
Conversation 3

English Speaker
English: Hello!
Tamil: வணக்கம்!
Pronunciation: Vanakkam!
"""

EMPTY_INPUT = ""
ONLY_SEPARATOR = "---"

# ---------------------------------------------------------------------------
# Tests: parse_conversations
# ---------------------------------------------------------------------------


class TestParseConversations:
    def test_single_conversation_count(self):
        convs = parse_conversations(SINGLE_CONVERSATION)
        assert len(convs) == 1

    def test_single_conversation_title(self):
        conv = parse_conversations(SINGLE_CONVERSATION)[0]
        assert conv.title == "Conversation 1"

    def test_english_speaker_english(self):
        conv = parse_conversations(SINGLE_CONVERSATION)[0]
        assert conv.english_speaker.english == "Good morning! How are you today?"

    def test_english_speaker_tamil(self):
        conv = parse_conversations(SINGLE_CONVERSATION)[0]
        assert "காலை வணக்கம்" in conv.english_speaker.tamil

    def test_english_speaker_pronunciation(self):
        conv = parse_conversations(SINGLE_CONVERSATION)[0]
        assert conv.english_speaker.pronunciation == "Kaalai vanakkam! Neengal eppadi irukkireergal?"

    def test_lote_speaker_english(self):
        conv = parse_conversations(SINGLE_CONVERSATION)[0]
        assert conv.lote_speaker.english == "I am fine, thank you. And you?"

    def test_lote_speaker_tamil(self):
        conv = parse_conversations(SINGLE_CONVERSATION)[0]
        assert "நான் நலமாக" in conv.lote_speaker.tamil

    def test_lote_speaker_pronunciation(self):
        conv = parse_conversations(SINGLE_CONVERSATION)[0]
        assert conv.lote_speaker.pronunciation == "Naan nalamaga irukkiren, nandri. Neengalo?"

    def test_two_conversations_count(self):
        convs = parse_conversations(TWO_CONVERSATIONS)
        assert len(convs) == 2

    def test_two_conversations_titles(self):
        convs = parse_conversations(TWO_CONVERSATIONS)
        assert convs[0].title == "Conversation 1"
        assert convs[1].title == "Conversation 2"

    def test_second_conversation_english_speaker(self):
        conv = parse_conversations(TWO_CONVERSATIONS)[1]
        assert conv.english_speaker.english == "I need to make an appointment with the doctor."

    def test_second_conversation_lote_pronunciation(self):
        conv = parse_conversations(TWO_CONVERSATIONS)[1]
        assert conv.lote_speaker.pronunciation == "Nichchayamaga. Ungalukkku enda naal vasadhiyaga irukkum?"

    def test_missing_lote_section_returns_empty(self):
        conv = parse_conversations(MISSING_SECTIONS)[0]
        assert conv.lote_speaker.english == ""
        assert conv.lote_speaker.pronunciation == ""

    def test_empty_input_returns_empty_list(self):
        convs = parse_conversations(EMPTY_INPUT)
        assert convs == []

    def test_only_separator_returns_empty_list(self):
        convs = parse_conversations(ONLY_SEPARATOR)
        # separator alone should not produce valid conversations (or just empty ones)
        for conv in convs:
            assert conv.english_speaker.english == ""
            assert conv.lote_speaker.pronunciation == ""

    def test_returns_conversation_objects(self):
        convs = parse_conversations(SINGLE_CONVERSATION)
        assert isinstance(convs[0], Conversation)
        assert isinstance(convs[0].english_speaker, Speaker)
        assert isinstance(convs[0].lote_speaker, Speaker)

    def test_case_insensitive_section_headers(self):
        text = """
Conversation X

english speaker
English: Hello world
Tamil: வணக்கம்
Pronunciation: Vanakkam

lote speaker
English: Hi there
Tamil: ஹாய்
Pronunciation: Haai
"""
        conv = parse_conversations(text)[0]
        assert conv.english_speaker.english == "Hello world"
        assert conv.lote_speaker.pronunciation == "Haai"

    def test_case_insensitive_field_keys(self):
        text = """
Conversation Y

English Speaker
ENGLISH: Test sentence
TAMIL: சோதனை
PRONUNCIATION: Soathanai

LOTE Speaker
ENGLISH: Response here
TAMIL: இங்கே பதில்
PRONUNCIATION: Ingey padhil
"""
        conv = parse_conversations(text)[0]
        assert conv.english_speaker.english == "Test sentence"
        assert conv.lote_speaker.pronunciation == "Ingey padhil"

    def test_full_sample_file(self, tmp_path):
        """The bundled sample_conversations.txt must parse cleanly."""
        sample = Path(__file__).parent / "sample_conversations.txt"
        if not sample.exists():
            pytest.skip("sample_conversations.txt not found")
        text = sample.read_text(encoding="utf-8")
        convs = parse_conversations(text)
        assert len(convs) >= 3
        for conv in convs:
            assert conv.english_speaker.english != ""
            assert conv.lote_speaker.pronunciation != ""


# ---------------------------------------------------------------------------
# Tests: build_output_filename
# ---------------------------------------------------------------------------


class TestBuildOutputFilename:
    def test_basic_title(self):
        name = build_output_filename("Conversation 1", 0)
        assert name == "Conversation_1.mp3"

    def test_special_characters_stripped(self):
        name = build_output_filename("Hello! World?", 0)
        assert name.endswith(".mp3")
        assert "!" not in name
        assert "?" not in name

    def test_empty_title_uses_index(self):
        name = build_output_filename("", 4)
        assert name == "conversation_5.mp3"

    def test_whitespace_normalised(self):
        name = build_output_filename("My   Conversation", 0)
        assert "   " not in name
        assert name.endswith(".mp3")
