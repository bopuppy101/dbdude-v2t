#!/usr/bin/env python3
"""
AVAudioEngine capture POC — proves we can capture mic audio via
AVAudioEngine + PyObjC and convert buffers to numpy float32.

Runs for 5 seconds, prints per-buffer info + final RMS. No rumps,
no FN key, no transcription — just the audio plumbing.

Run:
    source macos/venv/bin/activate
    python3 macos/experiments/avaudioengine_capture_poc.py
"""
import objc
import time
import ctypes
import numpy as np

# Load AVFoundation
objc.loadBundle('AVFoundation', globals(), '/System/Library/Frameworks/AVFoundation.framework')
AVAudioEngine = objc.lookUpClass('AVAudioEngine')
AVAudioFormat = objc.lookUpClass('AVAudioFormat')

# Shared state (GIL-protected list + primitives)
captured_chunks = []
buffer_count = 0
first_buffer_time = None
reported_format = {}


def audio_tap_callback(buffer, when):
    """Tap callback — fires on an audio thread. Keep it short."""
    global buffer_count, first_buffer_time

    try:
        frame_length = int(buffer.frameLength())
        fmt = buffer.format()

        if buffer_count == 0:
            first_buffer_time = time.time()
            reported_format['sample_rate'] = float(fmt.sampleRate())
            reported_format['channels'] = int(fmt.channelCount())
            reported_format['fcd_type'] = type(buffer.floatChannelData()).__name__

        buffer_count += 1

        # Extract samples from channel 0.
        # floatChannelData() returns float** (pointer to array of channel pointers).
        # PyObjC typically surfaces this as something addressable via ctypes.
        fcd = buffer.floatChannelData()
        if fcd is None:
            return

        # Strategy: cast the pointer to float** and read channel 0.
        try:
            addr = int(fcd) if hasattr(fcd, '__int__') else ctypes.addressof(fcd)
            float_ptr_ptr = ctypes.cast(addr, ctypes.POINTER(ctypes.POINTER(ctypes.c_float)))
            chan0 = float_ptr_ptr[0]
            samples = np.ctypeslib.as_array(chan0, shape=(frame_length,)).copy()
            captured_chunks.append(samples)
        except Exception as e:
            if buffer_count <= 3:
                print(f"  [extract error on buf {buffer_count}: {e}]", flush=True)

    except Exception as e:
        print(f"ERROR in tap: {e}", flush=True)


audio_tap_callback.__block_signature__ = b'v@?@@'


def main():
    print("=== AVAudioEngine Capture POC ===", flush=True)

    engine = AVAudioEngine.alloc().init()
    input_node = engine.inputNode()

    # Native input format (usually 44.1k or 48k, float32, 1-2 channels)
    input_format = input_node.inputFormatForBus_(0)
    print(f"Native input format: {input_format.sampleRate()}Hz, "
          f"{input_format.channelCount()} channel(s), "
          f"common={input_format.commonFormat()}", flush=True)

    # Install tap at native format — no resampling yet, that's phase 2.
    input_node.installTapOnBus_bufferSize_format_block_(
        0, 4096, input_format, audio_tap_callback
    )
    print("Tap installed on bus 0, buffer size 4096.", flush=True)

    engine.prepare()
    result = engine.startAndReturnError_(None)
    # startAndReturnError_ returns (BOOL, NSError*) as a tuple in PyObjC
    if isinstance(result, tuple):
        success, error = result
    else:
        success, error = result, None
    if not success:
        print(f"ERROR starting engine: {error}", flush=True)
        return

    print("\nEngine started. Speak now — capturing for 5 seconds...\n", flush=True)
    time.sleep(5)

    engine.stop()
    input_node.removeTapOnBus_(0)
    print("Engine stopped, tap removed.\n", flush=True)

    # Report
    print("=== Results ===", flush=True)
    print(f"Buffers received: {buffer_count}", flush=True)
    if reported_format:
        print(f"Reported sample rate: {reported_format['sample_rate']}Hz", flush=True)
        print(f"Reported channels: {reported_format['channels']}", flush=True)
        print(f"floatChannelData() Python type: {reported_format['fcd_type']}", flush=True)

    if captured_chunks:
        audio = np.concatenate(captured_chunks).flatten()
        print(f"Total samples captured: {len(audio)}", flush=True)
        print(f"Expected at {reported_format.get('sample_rate', 0)}Hz × 5s: "
              f"~{int(reported_format.get('sample_rate', 0) * 5)}", flush=True)
        rms = float(np.sqrt(np.mean(audio ** 2)))
        peak = float(np.max(np.abs(audio)))
        print(f"RMS: {rms:.4f}  (>0.005 means mic picked up sound)", flush=True)
        print(f"Peak: {peak:.4f}  (closer to 1.0 = louder)", flush=True)
        if rms > 0.005:
            print("SUCCESS: audio captured.", flush=True)
        else:
            print("WARNING: audio is near-silent — check mic or speak louder.", flush=True)
    else:
        print("FAIL: no samples extracted. Check floatChannelData() handling.", flush=True)


if __name__ == "__main__":
    main()
