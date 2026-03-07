# Voice2text, port to macOS. 

## Set up the virtual environment. 

# Create the repo directory
mkdir -p ~/git/macos-v2t
cd ~/git/macos-v2t

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install mlx-whisper sounddevice numpy pynput

# Save requirements
# pip freeze > requirements.txt

After doing a pip and stall... of 
pip install mlx-whisper
import mlx_whisper

result = mlx_whisper.transcribe(
    "audio.wav",
    path_or_hf_repo="mlx-community/whisper-medium.en-mlx"
)
print(result["text"]) 

