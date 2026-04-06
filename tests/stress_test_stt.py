import os
import sys
import json
import time
import shutil
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add V3 to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.audio_tools import SpeechToTextTool

# Constants for test file validation
REQUIRED_AUDIO_FILES = 5
SIMULATED_ERROR_FILES = 2

def file_exists_check(path, should_exist=True):
    """Verificação robusta de existência de arquivo antes do teste."""
    if not os.path.exists(path):
        if should_exist:
            logger.warning(f"File not found (expected): {path}")
            return False
        logger.info(f"File expected not found: {path}")
        return True
    return True

def safe_execute_tool(audio_path):
    """Executa o tool com validação de arquivo de áudio."""
    if not os.path.exists(audio_path):
        return json.dumps({
            "status": "error",
            "error": f"Audio file not found: {audio_path}"
        })
    
    if os.path.getsize(audio_path) == 0:
        return json.dumps({
            "status": "error",
            "error": "Empty audio file detected"
        })
    
    tool = SpeechToTextTool()
    return tool.execute(audio_path=audio_path)

def run_test(name, audio_path, expected_status="success"):
    """Testa um arquivo de áudio com verificação de pré-condições."""
    logger.info(f"Testing [{name}]...")
    result = {
        "name": name,
        "audio_path": audio_path,
        "expected": expected_status,
        "actual": None,
        "success": False,
        "latency": None,
        "error": None,
        "file_exists": os.path.exists(audio_path)
    }
    
    try:
        start_time = time.time()
        
        # Pré-validação de arquivo
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        raw_result = safe_execute_tool(audio_path)
        end_time = time.time()
        
        latency = end_time - start_time
        result["latency"] = latency
        
        # Robust JSON parsing with fallback
        try:
            data = json.loads(raw_result if raw_result else "{}")
        except (json.JSONDecodeError, TypeError) as parse_error:
            logger.error(f"Failed to parse tool response: {parse_error}")
            data = {"status": "error", "error": str(parse_error)}
        
        actual_status = data.get("status", "error")
        error_msg = data.get("error", None)
        result["actual"] = actual_status
        result["error"] = error_msg
        
        if expected_status == "success":
            is_success = actual_status == "success"
        else:
            is_success = actual_status == "error" or "error" in str(error_msg).lower()
        
        result["success"] = is_success
        
        logger.info(f"  - Status: {actual_status}")
        if error_msg:
            logger.info(f"  - Error: {error_msg}")
        logger.info(f"  - Latency: {latency:.2f}s")
        logger.info(f"  - Result: {'[PASS]' if is_success else '[FAIL]'}")
        
    except FileNotFoundError as e:
        result["error"] = str(e)
        logger.warning(f"  - FileNotFoundError: {e}")
        logger.info(f"  - Result: [SKIP] File missing - Expected: {expected_status}")
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"  - Exception: {e}")
        logger.info(f"  - Result: [FAIL] Unexpected exception")
    
    return result

def run_stress_tests(args):
    """Orquestra execução de todos os testes com cleanup garantido."""
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_dir = os.path.join(app_root, "tests", "audio_samples")
    results = []
    
    # Verifica existência do diretório base
    if not os.path.exists(base_dir):
        logger.error(f"Audio samples directory not found: {base_dir}")
        logger.warning("Creating default audio tests...")
        os.makedirs(base_dir, exist_ok=True)
    
    # Testes de áudio
    audio_tests = [
        ("Short (<5s)", os.path.join(base_dir, "short.wav")),
        ("Long (>2min)", os.path.join(base_dir, "long.wav")),
        ("Noisy Audio", os.path.join(base_dir, "noisy.wav")),
        ("Silent Audio", os.path.join(base_dir, "silent.wav")),
        ("Very Large File", os.path.join(base_dir, "large.wav")),
    ]
    
    for name, path in audio_tests:
        results.append(run_test(name, path, "success"))
        
        if args.fail_fast and not results[-1]["success"]:
            logger.warning("Stopping execution on first failure (-x/--fail-fast)")
            return results
    
    # Simulação de erro: Arquivo corrompido (se existir)
    corrupted_path = os.path.join(base_dir, "corrupted.wav")
    if os.path.exists(corrupted_path):
        results.append(run_test("Corrupted File", corrupted_path, "error"))
    else:
        logger.info(f"Simulated error skip: {corrupted_path} does not exist")
        results.append(run_test("Corrupted File", corrupted_path, "error"))
    
    # Simulação: BinarySimulator melhorado
    class BinarySimulator:
        """Context Manager para simular falhas de binary/model com cleanup automático."""
        def __init__(self, path, backup_ext=".bak"):
            self.path = path
            self.backup = path + backup_ext
            self.renamed = False
            self.original_exists = os.path.exists(path)
            
        def __enter__(self):
            if os.path.exists(self.path):
                os.rename(self.path, self.backup)
                self.renamed = True
                logger.info(f"  - Binary/Model moved to backup for simulation: {self.path}")
            else:
                logger.info(f"  - Binary/Model not found, skipping simulation: {self.path}")
                self.original_exists = False
            return self
            
        def __exit__(self, exc_type, exc_value, traceback):
            if self.renamed and os.path.exists(self.backup):
                try:
                    os.rename(self.backup, self.path)
                    logger.info(f"  - Binary/Model restored")
                except OSError as e:
                    logger.warning(f"  - WARNING: Failed to restore binary/model: {e}")
                    self.renamed = False
            return False
    
    # Simulação: Whisper binary missing
    print("\n--- Failure Simulation: Missing Binary ---")
    whisper_bin = os.path.join(app_root, "libs", "whisper.cpp", "build", "bin", "whisper-cli")
    with BinarySimulator(whisper_bin):
        test_results = run_test("Binary Missing", os.path.join(base_dir, "short.wav"), "error")
        results.append(test_results)
    
    # Simulação: Model missing
    print("\n--- Failure Simulation: Missing Model ---")
    whisper_model = os.path.join(app_root, "libs", "whisper.cpp", "models", "ggml-base.bin")
    with BinarySimulator(whisper_model):
        test_results = run_test("Model Missing", os.path.join(base_dir, "short.wav"), "error")
        results.append(test_results)
    
    return results

def generate_report(results):
    """Gera relatório final estruturado."""
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    skipped = sum(1 for r in results if r.get("file_exists", False) is False)
    
    # Filtra apenas resultados com latência válida
    valid_latencies = [r["latency"] for r in results if r["latency"] is not None]
    total_latency = sum(valid_latencies)
    avg_latency = total_latency / len(valid_latencies) if valid_latencies else 0
    
    print("\n" + "="*50)
    print("STRESS TEST SUMMARY")
    print("="*50)
    print(f"{'Test Name':<28} | {'Status':<7} | {'Latency':>12} | {'Expected'}")
    print("-"*50)
    
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        name = r["name"][:26]
        latency = f"{r['latency']:.2f}s" if r["latency"] else "N/A"
        expected = r["expected"]
        
        print(f"{name:<28} | {status:<7} | {latency:>12} | {expected}")
    
    print("="*50)
    print(f"Total Tested: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped (files missing): {skipped}")
    print(f"Average Latency: {avg_latency:.2f}s")
    print("="*50)
    
    # Exportar JSON para CI/CD integration
    report_data = {
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "all_results": [r for r in results],
        "average_latency": round(avg_latency, 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "app_root": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    }
    
    output_file = os.path.join(
        os.path.dirname(__file__),
        "stress_test_results.json"
    )
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"\nReport saved to: {output_file}")
    return report_data

def main():
    """Entry point com argparse para suporte a flags."""
    parser = argparse.ArgumentParser(
        description="Arkanis V3 - STT Stress Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python stress_test_stt.py                           # Run all tests
  python stress_test_stt.py --fail-fast               # Stop on first failure
  python stress_test_stt.py -o custom_report.json     # Custom output file
        """
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file for JSON report"
    )
    parser.add_argument(
        "--fail-fast", "-x",
        action="store_true",
        help="Stop on first failure"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce console output verbosity"
    )
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    results = run_stress_tests(args)
    report = generate_report(results)
    
    if report["failed"] > 0:
        logger.error("Some tests failed. Check the detailed report.")
        sys.exit(1)
    
    logger.info("All tests passed successfully!")
    sys.exit(0)

if __name__ == "__main__":
    main()
