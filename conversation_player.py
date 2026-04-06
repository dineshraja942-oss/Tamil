#!/usr/bin/env python3
"""
conversation_player.py
======================
Parses Tamil NAATI-style conversation files and generates combined audio:

  1. English Speaker  → English content  (spoken in English)
  2. 15-second silence gap
  3. LOTE Speaker     → Pronunciation    (spoken in English)

Usage
-----
    # Generate a single combined MP3 for every conversation in the file:
    python3 conversation_player.py sample_conversations.txt

    # Specify a custom output directory:
    python3 conversation_player.py sample_conversations.txt --output-dir ./audio_output

    # Also play each audio clip immediately after generating it (requires ffplay/mpg123):
    python3 conversation_player.py sample_conversations.txt --play

Input file format
-----------------
    Conversation 1

    English Speaker
    English: <english text>
    Tamil: <tamil text>
    Pronunciation: <pronunciation text>

    LOTE Speaker
    English: <english text>
    Tamil: <tamil text>
    Pronunciation: <pronunciation text>

    ---

    Conversation 2
    ...

Conversations are separated by lines containing only '---'.
"""

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    from gtts import gTTS
except ImportError:
    sys.exit("gtts is not installed. Run:  pip install gtts")

try:
    from pydub import AudioSegment
except ImportError:
    sys.exit("pydub is not installed. Run:  pip install pydub")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Speaker:
    english: str = ""
    tamil: str = ""
    pronunciation: str = ""


@dataclass
class Conversation:
    title: str = ""
    english_speaker: Speaker = field(default_factory=Speaker)
    lote_speaker: Speaker = field(default_factory=Speaker)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_FIELD_PATTERNS: dict = {}


def _field_pattern(key: str) -> re.Pattern:
    """Return a compiled regex for 'Key: value', cached by key name."""
    if key not in _FIELD_PATTERNS:
        _FIELD_PATTERNS[key] = re.compile(
            rf"^\s*{re.escape(key)}\s*:\s*(.*)", re.IGNORECASE
        )
    return _FIELD_PATTERNS[key]


def _extract_field(lines: List[str], key: str) -> str:
    """Return the value after 'Key:' from a list of lines (case-insensitive key match)."""
    pattern = _field_pattern(key)
    for line in lines:
        m = pattern.match(line)
        if m:
            return m.group(1).strip()
    return ""


def _parse_speaker_block(lines: List[str]) -> Speaker:
    return Speaker(
        english=_extract_field(lines, "English"),
        tamil=_extract_field(lines, "Tamil"),
        pronunciation=_extract_field(lines, "Pronunciation"),
    )


def parse_conversations(text: str) -> List[Conversation]:
    """
    Parse a string containing one or more conversation blocks separated by '---'.
    Returns a list of Conversation objects.
    """
    raw_blocks = re.split(r"\n\s*---\s*\n", text)
    conversations: List[Conversation] = []

    for raw in raw_blocks:
        raw = raw.strip()
        if not raw:
            continue

        conv = Conversation()

        # Split into lines and find section boundaries
        lines = raw.splitlines()

        # Title: first non-empty line (e.g. "Conversation 1")
        for line in lines:
            if line.strip():
                conv.title = line.strip()
                break

        # Find 'English Speaker' and 'LOTE Speaker' section headers
        eng_start = lote_start = None
        for i, line in enumerate(lines):
            if re.match(r"^\s*English\s+Speaker\s*$", line, re.IGNORECASE):
                eng_start = i
            elif re.match(r"^\s*LOTE\s+Speaker\s*$", line, re.IGNORECASE):
                lote_start = i

        if eng_start is not None:
            end = lote_start if lote_start is not None else len(lines)
            conv.english_speaker = _parse_speaker_block(lines[eng_start + 1: end])

        if lote_start is not None:
            conv.lote_speaker = _parse_speaker_block(lines[lote_start + 1:])

        conversations.append(conv)

    return conversations


# ---------------------------------------------------------------------------
# Audio generation
# ---------------------------------------------------------------------------

GAP_SECONDS = 15
_PREVIEW_LENGTH = 60


def _truncate(text: str, max_len: int = _PREVIEW_LENGTH) -> str:
    """Return text truncated to max_len characters with an ellipsis if needed."""
    return text[:max_len] + "..." if len(text) > max_len else text


def _tts_segment(text: str, lang: str = "en") -> AudioSegment:
    """Generate a gTTS AudioSegment from text.

    Raises:
        RuntimeError: if gTTS fails (e.g. no network connection).
    """
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(tmp_path)
        segment = AudioSegment.from_mp3(tmp_path)
        return segment
    except Exception as exc:
        raise RuntimeError(
            f"TTS generation failed for text '{text[:60]}...': {exc}\n"
            "Ensure you have a working internet connection (gTTS requires access to Google's API)."
        ) from exc
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _silence_segment(seconds: int) -> AudioSegment:
    return AudioSegment.silent(duration=seconds * 1000)


def generate_audio(conv: Conversation) -> Optional[AudioSegment]:
    """
    Build audio for a single conversation:
      [English Speaker – English] + [15 s silence] + [LOTE Speaker – Pronunciation]

    Returns None if both required text fields are empty.
    """
    eng_text = conv.english_speaker.english
    lote_pronunciation = conv.lote_speaker.pronunciation

    if not eng_text and not lote_pronunciation:
        print(f"  WARNING: '{conv.title}' has no English or Pronunciation text – skipping.", file=sys.stderr)
        return None

    segments: List[AudioSegment] = []

    if eng_text:
        print(f"  Generating English Speaker audio: \"{_truncate(eng_text)}\"")
        segments.append(_tts_segment(eng_text, lang="en"))
    else:
        print("  WARNING: English Speaker has no English content.", file=sys.stderr)

    segments.append(_silence_segment(GAP_SECONDS))

    if lote_pronunciation:
        print(f"  Generating LOTE Speaker pronunciation audio: \"{_truncate(lote_pronunciation)}\"")
        segments.append(_tts_segment(lote_pronunciation, lang="en"))
    else:
        print("  WARNING: LOTE Speaker has no Pronunciation content.", file=sys.stderr)

    combined = segments[0]
    for seg in segments[1:]:
        combined = combined + seg

    return combined


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_output_filename(title: str, index: int) -> str:
    safe = re.sub(r"[^\w\s-]", "", title).strip()
    safe = re.sub(r"[\s]+", "_", safe)
    if not safe:
        safe = f"conversation_{index + 1}"
    return f"{safe}.mp3"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate TTS audio for Tamil NAATI-style conversation files."
    )
    parser.add_argument(
        "input_file",
        help="Path to the conversation text file.",
    )
    parser.add_argument(
        "--output-dir",
        default="audio_output",
        help="Directory where audio files will be saved (default: audio_output).",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="Play each audio file immediately after generating it (requires ffplay or mpg123).",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input_file)
    if not input_path.is_file():
        print(f"ERROR: File not found: {input_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    text = input_path.read_text(encoding="utf-8")
    conversations = parse_conversations(text)

    if not conversations:
        print("No conversations found in the input file.", file=sys.stderr)
        return 1

    print(f"Found {len(conversations)} conversation(s) in '{input_path}'.")
    print(f"Output directory: '{output_dir}'")
    print()

    generated = 0
    for i, conv in enumerate(conversations):
        print(f"[{i + 1}/{len(conversations)}] Processing: {conv.title or f'Conversation {i + 1}'}")
        audio = generate_audio(conv)
        if audio is None:
            continue

        filename = build_output_filename(conv.title or f"conversation_{i + 1}", i)
        out_path = output_dir / filename
        audio.export(str(out_path), format="mp3")
        print(f"  Saved: {out_path}")
        generated += 1

        if args.play:
            _play_audio(str(out_path))

        print()

    print(f"Done. {generated}/{len(conversations)} audio file(s) generated in '{output_dir}'.")
    return 0


def _play_audio(path: str) -> None:
    """Attempt to play an audio file using available system tools."""
    import shutil
    import subprocess

    for player in ("ffplay", "mpg123", "mpg321", "aplay"):
        if shutil.which(player):
            args = [player]
            if player == "ffplay":
                args += ["-nodisp", "-autoexit"]
            args.append(path)
            subprocess.run(args, check=False)
            return
    print("  (no audio player found – install ffplay or mpg123 to enable --play)")


if __name__ == "__main__":
    sys.exit(main())
