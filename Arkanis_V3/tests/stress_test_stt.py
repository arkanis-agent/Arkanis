import os
import sys
import json
import time
import shutil

# Add V3 to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.audio_tools import SpeechToTextTool

def run_test(name, audio_path, expected_status="success"):
    print(f"Testing [{name}]...")
    tool = SpeechToTextTool()
    
    start_time = time.time()
    result_json = tool.execute(audio_path=audio_path)
    end_time = time.time()
    
    latency = end_time - start_time
    data = json.loads(result_json)
    
    status = data.get("status", "error")
    error = data.get("error", None)
    
    print(f"  - Status: {status}")
    if error:
        print(f"  - Error: {error}")
    print(f"  - Latency: {latency:.2f}s")
    
    if expected_status == "success":
        if status == "success":
            print(f"  - Result: [PASS]")
            return True, latency
        else:
            print(f"  - Result: [FAIL] Expected success, got error.")
            return False, latency
    else:
        if "error" in data:
            print(f"  - Result: [PASS] Expected error, got error.")
            return True, latency
        else:
            print(f"  - Result: [FAIL] Expected error, got success.")
            return False, latency

def main():
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_dir = os.path.join(app_root, "tests", "audio_samples")
    
    results = []
    
    # 1. Short (1s)
    results.append(("Short (<5s)", run_test("Short Audio", os.path.join(base_dir, "short.wav"))))
    
    # 2. Long (2min)
    results.append(("Long (>2min)", run_test("Long Audio", os.path.join(base_dir, "long.wav"))))
    
    # 3. Noisy
    results.append(("Noisy Audio", run_test("Noisy Audio", os.path.join(base_dir, "noisy.wav"))))
    
    # 4. Silent
    results.append(("Silent Audio", run_test("Silent Audio", os.path.join(base_dir, "silent.wav"))))
    
    # 5. Corrupted
    results.append(("Corrupted File", run_test("Corrupted File", os.path.join(base_dir, "corrupted.wav"), expected_status="error")))
    
    # 6. Unsupported Format
    # The tool uses ffmpeg to convert, so if it's not a real audio file, ffmpeg should fail.
    results.append(("Unsupported Format", run_test("Unsupported Format", os.path.join(base_dir, "unsupported.mp3"), expected_status="error")))
    
    # 7. Very Large File
    results.append(("Very Large File", run_test("Very Large File", os.path.join(base_dir, "large.wav"))))
    
    # Failure Simulation: Whisper binary missing
    print("\n--- Failure Simulation: Missing Binary ---")
    whisper_bin = os.path.join(app_root, "libs", "whisper.cpp", "build", "bin", "whisper-cli")
    whisper_bin_bak = whisper_bin + ".bak"
    if os.path.exists(whisper_bin):
        os.rename(whisper_bin, whisper_bin_bak)
        results.append(("Binary Missing", run_test("Binary Missing", os.path.join(base_dir, "short.wav"), expected_status="error")))
        os.rename(whisper_bin_bak, whisper_bin)
    
    # Failure Simulation: Model missing
    print("\n--- Failure Simulation: Missing Model ---")
    whisper_model = os.path.join(app_root, "libs", "whisper.cpp", "models", "ggml-base.bin")
    whisper_model_bak = whisper_model + ".bak"
    if os.path.exists(whisper_model):
        os.rename(whisper_model, whisper_model_bak)
        results.append(("Model Missing", run_test("Model Missing", os.path.join(base_dir, "short.wav"), expected_status="error")))
        os.rename(whisper_model_bak, whisper_model)

    # Final Report
    print("\n" + "="*30)
    print("STRESS TEST SUMMARY")
    print("="*30)
    for name, (success, latency) in results:
        status_str = "PASS" if success else "FAIL"
        print(f"{name:20} : {status_str} (Latency: {latency:.2f}s)")
    print("="*30)

if __name__ == "__main__":
    main()
