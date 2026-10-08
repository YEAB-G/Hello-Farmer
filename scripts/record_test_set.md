# Test Set Collection Protocol (scripts/record_test_set.md)

This document establishes the recording and annotation methodology for collecting the Hello Farmer real-caller evaluation dataset.

---

## 1. Objectives & Scope
- **Target Size**: 50 to 100 spoken utterances per language (Amharic and Afaan Oromo).
- **Domain**: Authentic agricultural queries regarding teff, wheat, and maize crops, weather conditions, pest symptoms, and fertilizer usage.
- **Goal**: Measure Speech-to-Text Word Error Rate (WER) and Character Error Rate (CER) under realistic acoustic conditions encountered in rural Ethiopia.

---

## 2. Demographic & Acoustic Diversity
To prevent overfitting to clean studio audio, recordings must cover:
1. **Gender Balance**: ~50% female, ~50% male speakers.
2. **Age Distribution**:
   - Youth (18–30): ~25%
   - Middle-age (31–50): ~50%
   - Older adults (50+): ~25%
3. **Dialect / Accent Variations**:
   - Amharic: Central (Shewa), Gojjam, Wollo, Gondar.
   - Afaan Oromo: Central (Shewa/Tulama), Western (Wollega), Eastern (Hararghe), Southern (Arsi/Bale).
4. **Noise Profiles**:
   - Clean / Indoor room (quiet background).
   - Outdoor farm field (wind, distant livestock, ambient environmental sounds).
   - Roadside / Village market (traffic noise, overlapping voices).

---

## 3. Recording Setup
1. **Handset & Transport**:
   - Primary: Standard Android phone microphone (mimicking softphone use over 3G/4G).
   - Secondary: Audio captured through Asterisk SIP channel over G.711u/G.711a codec.
2. **Audio Specifications**:
   - Format: WAV, 16 kHz sample rate, 16-bit linear PCM, mono.
   - Secondary Narrowband Set: 8 kHz sample rate, 16-bit linear PCM (downsampled and upsampled), plus G.711 companded audio.

---

## 4. Transcription & Annotation Rules
1. **Verbatim Fidelity**: Transcribe exactly what is spoken, including hesitations, regional dialect words, and colloquial agricultural terms.
2. **Script Formatting**:
   - Amharic: Standard Ge'ez script (Unicode Range `U+1200` to `U+137F`).
   - Afaan Oromo: Standard Latin Qubee script.
3. **Numbers**: Write all spoken numbers as spelled-out words in the reference text (e.g., Amharic: "ሁለት ሄክታር", not "2 ሄክታር").
4. **Metadata Record**:
   - File ID (`clip_001.wav`)
   - Language (`am` or `om`)
   - Speaker ID, gender, age bracket
   - Environment condition (`quiet`, `wind`, `crowd`)
   - Reference verbatim transcript
