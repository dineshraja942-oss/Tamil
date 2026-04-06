# Tamil NAATI Conversation Player

A Python tool that processes Tamil NAATI-style conversation files and generates
combined audio output:

1. **English Speaker** → speaks the English content
2. **15-second silence** (gap for the candidate/listener)
3. **LOTE Speaker** → speaks the Tamil pronunciation (romanised)

---

## Conversation file format

Conversations are separated by `---` lines:

```
Conversation 1

English Speaker
English: Good morning! How are you today?
Tamil: காலை வணக்கம்! நீங்கள் எப்படி இருக்கிறீர்கள்?
Pronunciation: Kaalai vanakkam! Neengal eppadi irukkireergal?

LOTE Speaker
English: I am fine, thank you. And you?
Tamil: நான் நலமாக இருக்கிறேன், நன்றி. நீங்களோ?
Pronunciation: Naan nalamaga irukkiren, nandri. Neengalo?

---

Conversation 2
...
```

See [`sample_conversations.txt`](sample_conversations.txt) for a ready-to-use example.

---

## Installation

```bash
pip install -r requirements.txt
```

> **Note:** `gTTS` requires an active internet connection (it calls Google's
> Text-to-Speech API). `pydub` requires **ffmpeg** to be installed:
>
> * macOS: `brew install ffmpeg`
> * Ubuntu/Debian: `sudo apt install ffmpeg`
> * Windows: download from <https://ffmpeg.org/download.html>

---

## Usage

```bash
# Generate one MP3 per conversation (saved to ./audio_output/)
python3 conversation_player.py sample_conversations.txt

# Specify a custom output directory
python3 conversation_player.py sample_conversations.txt --output-dir ./my_audio

# Generate and play each file immediately (requires ffplay or mpg123)
python3 conversation_player.py sample_conversations.txt --play
```

Each generated MP3 contains:

| Segment | Content |
|---------|---------|
| 0 s | English Speaker reading the **English** text |
| after English audio | **15 seconds of silence** |
| after gap | LOTE Speaker reading the **Pronunciation** text |

---

## Running tests

```bash
python3 -m pytest test_conversation_player.py -v
```
