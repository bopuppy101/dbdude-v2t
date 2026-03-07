# Minimizing Background Noise Impact on Transcription

## The Problem

When Whisper receives audio with background noise or silence, it can "hallucinate" - generating text that wasn't actually spoken. Common hallucinations include:
- Repeated words: "Okay. Okay. Okay. Okay."
- Filler phrases: "Thank you for watching", "Subscribe to my channel"
- Random words that fit the noise pattern

This happens because Whisper is trained to always produce output, even when input is unclear.

---

## Solution Options

### 1. RMS Threshold (Simplest)

**What it is:** Measure the audio volume (Root Mean Square) and skip transcription if too quiet.

**How it works:**
```python
rms = np.sqrt(np.mean(audio**2))
if rms < 0.01:  # Threshold - adjust as needed
    print("Audio too quiet, skipping transcription")
    return
```

**Pros:**
- Dead simple to implement
- No additional dependencies
- Very fast

**Cons:**
- Can't distinguish quiet speech from loud background noise
- Threshold needs manual tuning
- Binary decision (transcribe or not)

---

### 2. Silero VAD (Voice Activity Detection)

**What it is:** A small neural network trained specifically to detect human speech in audio.

**How it works:**
- Takes audio input
- Returns probability (0.0 to 1.0) that speech is present
- Runs in milliseconds with minimal CPU usage

**Installation:**
```bash
pip install silero-vad
# or
pip install torch torchaudio  # Silero uses PyTorch
```

**Basic Usage:**
```python
import torch
torch.set_num_threads(1)

model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=False)

(get_speech_timestamps,
 save_audio,
 read_audio,
 VADIterator,
 collect_chunks) = utils

# Check if speech is present
speech_prob = model(audio_chunk, sample_rate)
if speech_prob < 0.5:
    print("No speech detected, skipping transcription")
    return
```

**Advanced Usage - Get Speech Timestamps:**
```python
# Get timestamps of speech segments
speech_timestamps = get_speech_timestamps(audio, model, sampling_rate=16000)

# If no speech segments found, skip transcription
if not speech_timestamps:
    print("No speech detected")
    return

# Optionally, only transcribe the speech segments
speech_only = collect_chunks(speech_timestamps, audio)
result = whisper.transcribe(speech_only, ...)
```

**Pros:**
- Very accurate at detecting human speech
- Distinguishes speech from noise (fans, traffic, music)
- Can extract only speech portions from audio
- Fast (runs in milliseconds)
- Small model size (~2MB)

**Cons:**
- Additional dependency (PyTorch)
- Slightly more complex integration
- Small latency overhead

**Why Silero VAD?**
- Pre-trained on massive speech datasets
- Works across languages
- Handles various noise conditions
- MIT licensed, free for commercial use
- Active development and community

---

### 3. Whisper's Built-in Parameters

**What it is:** Whisper has some parameters to handle silence/noise.

**Available parameters (may vary by implementation):**
```python
result = mlx_whisper.transcribe(
    audio,
    path_or_hf_repo=model_path,
    no_speech_threshold=0.6,          # Skip segments with high no-speech probability
    condition_on_previous_text=False,  # Prevent hallucination buildup
    compression_ratio_threshold=2.4,   # Skip segments that seem repetitive
)
```

**Pros:**
- Built into Whisper, no extra dependencies
- Handles detection during transcription

**Cons:**
- Still processes the audio (uses GPU/CPU time)
- Parameters may not be available in all Whisper implementations
- Less control than pre-filtering

---

### 4. Minimum Duration Check

**What it is:** Skip recordings that are too short to contain meaningful speech.

**How it works:**
```python
if recording_duration < 0.3:  # Less than 300ms
    print("Recording too short, skipping")
    return
```

**Pros:**
- Trivial to implement
- Catches accidental key presses

**Cons:**
- Doesn't address noise in longer recordings

---

### 5. Post-Processing Filters

**What it is:** Filter out known hallucination patterns from the output.

**How it works:**
```python
# Common Whisper hallucinations
HALLUCINATIONS = [
    "thank you for watching",
    "thanks for watching",
    "subscribe to my channel",
    "see you next time",
]

def filter_hallucinations(text):
    text_lower = text.lower().strip()
    for pattern in HALLUCINATIONS:
        if pattern in text_lower:
            return ""  # Or remove just that phrase
    return text
```

**Pros:**
- Simple to implement
- Catches known patterns

**Cons:**
- Reactive, not proactive
- Can't catch all hallucinations
- Might false-positive on legitimate speech

---

## Recommended Approach

For dbdude-v2t, a layered approach:

1. **Minimum duration check** (trivial, catches accidental presses)
2. **RMS threshold OR Silero VAD** (pre-filter before Whisper)
3. **Whisper parameters** (if available in mlx_whisper)

### Simple Implementation (RMS):
```python
def should_transcribe(audio, min_duration=0.3, min_rms=0.01):
    """Check if audio is worth transcribing."""
    duration = len(audio) / SAMPLE_RATE
    if duration < min_duration:
        return False, "Too short"

    rms = np.sqrt(np.mean(audio**2))
    if rms < min_rms:
        return False, "Too quiet"

    return True, "OK"
```

### Better Implementation (Silero VAD):
```python
def should_transcribe(audio, min_duration=0.3, speech_threshold=0.5):
    """Check if audio contains speech worth transcribing."""
    duration = len(audio) / SAMPLE_RATE
    if duration < min_duration:
        return False, "Too short"

    speech_prob = vad_model(audio, SAMPLE_RATE)
    if speech_prob < speech_threshold:
        return False, f"No speech detected (prob={speech_prob:.2f})"

    return True, "OK"
```

---

## Resources

- [Silero VAD GitHub](https://github.com/snakers4/silero-vad)
- [Silero VAD Documentation](https://github.com/snakers4/silero-vad/wiki)
- [PyTorch Hub - Silero Models](https://pytorch.org/hub/snakers4_silero-vad_vad/)
