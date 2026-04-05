import os
import sys
import json
import unittest
import tempfile

# Add V3 to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.audio_tools import SpeechToTextTool

class TestSpeechToTextTool(unittest.TestCase):
    def setUp(self):
        self.tool = SpeechToTextTool()

    def test_instance(self):
        self.assertEqual(self.tool.name, "speech_to_text")
        self.assertTrue("temp_input" in self.tool.arguments or "audio_path" in self.tool.arguments)

    def test_execution_no_file(self):
        result = self.tool.execute(audio_path="non_existent_file.wav")
        data = json.loads(result)
        self.assertIn("error", data)
        err = data["error"].lower()
        self.assertTrue("not found" in err or "não encontrado" in err)

    def test_binary_check(self):
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
            temp_file.write(b"dummy")
            temp_file.flush()

            result = self.tool.execute(temp_input=temp_file.name)
            data = json.loads(result)

            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            whisper_cli_path = os.path.join(app_root, "libs", "whisper.cpp", "build", "bin", "whisper-cli")

            if not os.path.exists(whisper_cli_path):
                self.assertIn("error", data)
                err = data["error"].lower()
                self.assertTrue("install_whisper.sh" in err or "whisper" in err)

if __name__ == "__main__":
    unittest.main()