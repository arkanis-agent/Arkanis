import subprocess
import os

def generate_audio():
    base_dir = "/home/diego/Área de trabalho/Arkanis_V3.1/V3/tests/audio_samples"
    os.makedirs(base_dir, exist_ok=True)
    
    print(f"Generating test audio files in {base_dir}...")
    
    # 1. Short audio (1s of sine wave)
    short_file = os.path.join(base_dir, "short.wav")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=1", short_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 2. Long audio (2min of silence)
    long_file = os.path.join(base_dir, "long.wav")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=duration=125", long_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 3. Noisy audio (10s of white noise)
    noisy_file = os.path.join(base_dir, "noisy.wav")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=d=10", noisy_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 4. Silent audio (5s of silence)
    silent_file = os.path.join(base_dir, "silent.wav")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=duration=5", silent_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 5. Very large file (1min of sine wave, but higher bitrate/samplerate to make it bigger)
    large_file = os.path.join(base_dir, "large.wav")
    # 96kHz, stereo, 24-bit PCM for a 1min file to increase size
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=60",
        "-ar", "96000", "-ac", "2", "-c:a", "pcm_s24le", large_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 6. Corrupted file (just some random bytes)
    corrupted_file = os.path.join(base_dir, "corrupted.wav")
    with open(corrupted_file, "wb") as f:
        f.write(os.urandom(1024))
    
    # 7. Unsupported format (renamed text file)
    unsupported_file = os.path.join(base_dir, "unsupported.mp3")
    with open(unsupported_file, "w") as f:
        f.write("This is not a real mp3 file.")

    print("Audio generation complete.")

if __name__ == "__main__":
    generate_audio()
