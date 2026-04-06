import subprocess
import os
import sys
from pathlib import Path
import argparse


def generate_audio(output_dir=None, verbose=False):
    """Gera arquivos de áudio de teste com caminhos configuráveis."""
    if output_dir is None:
        # Tentar usar path relativo ao projeto primeiro, senão padrão local
        project_root = Path(__file__).resolve().parent.parent.parent
        output_dir = project_root / "V3" / "tests" / "audio_samples"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    def log(msg, level="info"):
        if verbose or level == "error":
            print(f"[{level.upper()}] {msg}")
    
    log(f"Gerando arquivos de teste em {output_dir}", "info")
    
    test_files = [
        {"name": "short.wav", "args": ["-f", "lavfi", "-i", "sine=frequency=1000:duration=1"]},
        {"name": "long.wav", "args": ["-f", "lavfi", "-i", "anullsrc=duration=5"]},  # Changed from 125s
        {"name": "noisy.wav", "args": ["-f", "lavfi", "-i", "anullsrc=duration=10,n=1"]},  # Fixed noise syntax
        {"name": "silent.wav", "args": ["-f", "lavfi", "-i", "anullsrc=duration=5"]},
        {"name": "large.wav", "args": ["-f", "lavfi", "-i", "sine=frequency=440:duration=60", "-ar", "96000", "-ac", "2", "-c:a", "pcm_s24le"]},
    ]
    
    for test in test_files:
        file_path = output_dir / test["name"]
        try:
            result = subprocess.run(
                ["ffmpeg", "-y"] + test["args"] + [str(file_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )
            if result.returncode != 0:
                log(f"Falha ao criar {test['name']}: {result.stderr.decode('utf-8')}", "error")
                continue
            log(f"Arquivo criado: {test['name']}", "info")
        except subprocess.TimeoutExpired:
            log(f"Tempo esgotado para {test['name']}", "error")
        except FileNotFoundError:
            log("ffmpeg não encontrado. Instale o ffmpeg.", "error")
        except Exception as e:
            log(f"Erro ao criar {test['name']}: {str(e)}", "error")
    
    # Arquivos especiais
    try:
        corrupted_file = output_dir / "corrupted.wav"
        with open(corrupted_file, "wb") as f:
            f.write(bytes(os.urandom(1024)))
        log("Arquivo corrompido criado", "info")
    except Exception as e:
        log(f"Erro ao criar arquivo corrompido: {str(e)}", "error")
    
    try:
        unsupported_file = output_dir / "unsupported.mp3"
        with open(unsupported_file, "w") as f:
            f.write("Not a valid mp3")
        log("Arquivo com formato inválido criado", "info")
    except Exception as e:
        log(f"Erro ao criar arquivo inválido: {str(e)}", "error")
    
    # Validação final
    generated = list(output_dir.iterdir())
    log(f"Processo concluído. {len(generated)} arquivo(s) gerados.", "info")
    
    return len(generated)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerar arquivos de áudio de teste para Arkanis V3")
    parser.add_argument("-o", "--output", help="Caminho de saída para os arquivos", default=None)
    parser.add_argument("-v", "--verbose", action="store_true", help="Saida verbose")
    
    args = parser.parse_args()
    generate_audio(output_dir=args.output, verbose=args.verbose)
    sys.exit(0)