import os
import sys
import json

# Add V3 to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.audio_tools import SpeechToTextTool

def test_stt_tool_instance():
    tool = SpeechToTextTool()
    assert tool.name == "speech_to_text"
    assert "audio_path" in tool.arguments

def test_stt_tool_execution_no_file():
    tool = SpeechToTextTool()
    result = tool.execute(audio_path="non_existent_file.wav")
    data = json.loads(result)
    assert "error" in data
    assert "not found" in data["error"]

def test_stt_tool_binary_check():
    # If binary is missing, it should return a helpful error
    tool = SpeechToTextTool()
    # Create a dummy file to pass the file check
    with open("dummy.wav", "w") as f:
        f.write("dummy")
    
    result = tool.execute(audio_path="dummy.wav")
    data = json.loads(result)
    
    os.remove("dummy.wav")
    
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(os.path.join(app_root, "libs", "whisper.cpp", "build", "bin", "whisper-cli")):
        assert "error" in data
        assert "install_whisper.sh" in data["error"]

if __name__ == "__main__":
    print("Running STT Tool Tests...")
    try:
        test_stt_tool_instance()
        print("✓ test_stt_tool_instance passed")
        test_stt_tool_execution_no_file()
        print("✓ test_stt_tool_execution_no_file passed")
        test_stt_tool_binary_check()
        print("✓ test_stt_tool_binary_check passed")
        print("\nAll baseline tests passed!")
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)
