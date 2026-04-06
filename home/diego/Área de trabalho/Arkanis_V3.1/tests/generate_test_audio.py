import subprocess
import os
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

def generate_audio():
    base_dir = os.environ.get('ARKANIS_AUDIO_DIR', Path.home() / 'Arkanis_V3' / 'tests' / 'audio_samples')
    
    try:
        Path(base_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Gerando arquivos de teste de áudio em {base_dir}...")
        
        # Verificação de dependência
        if not _check_ffmpeg_available():
            logger.error("FFmpeg não encontrado. Instale o FFmpeg para gerar os arquivos.")
            return False
        
        tests = [
            {'name': 'short.wav', 'command': ['sine=frequency=1000', 'duration=1']},
            {'name': 'long.wav', 'command': ['anullsrc', 'duration=125']},
            {'name': 'noisy.wav', 'command': ['anoisesrc', 'd=10']},
            {'name': 'silent.wav', 'command': ['anullsrc', 'duration=5']},
            {'name': 'large.wav', 'command': ['sine=frequency=440', 'duration=60', '-ar', '96000', '-ac', '2', '-c:a', 'pcm_s24le']},
        ]
        
        for test in tests:
            if not _generate_audio_test(test['name'], base_dir, test['command'], logger):
                logger.error(f"Falha ao gerar {test['name']}")
                return False
        
        _generate_corrupted_file(Path(base_dir) / 'corrupted.wav')
        _generate_unsupported_format(Path(base_dir) / 'unsupported.mp3')
        
        logger.info("Geração de arquivos de áudio concluída com sucesso.")
        return True
    
    except Exception as e:
        logger.error(f"Erro na geração de áudio: {e}")
        return False

def _check_ffmpeg_available():
    try:
        result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def _generate_audio_test(filename, base_dir, params, logger):
    """Gera um arquivo de teste de áudio com FFmpeg com tratamento de erro."""
    file_path = Path(base_dir) / filename
    try:
        cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i'] + params + [str(file_path)]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg erro em {filename}: {result.stderr}")
            return False
        
        # Validação do arquivo gerado
        if isinstance(file_path, Path):
            if not file_path.exists() or file_path.stat().st_size == 0:
                logger.error(f"Arquivo {filename} não foi criado ou está vazio.")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Erro ao gerar {filename}: {e}")
        return False

def _generate_corrupted_file(path):
    """Gera arquivo corrompido com bytes aleatórios."""
    try:
        with open(path, 'wb') as f:
            f.write(os.urandom(1024))
        logger.info(f"Arquivo corrompido gerado: {path}")
    except Exception as e:
        logger.error(f"Erro ao gerar arquivo corrompido: {e}")

def _generate_unsupported_format(path):
    """Gera arquivo de formato inválido."""
    try:
        with open(path, 'w') as f:
            f.write("This is not a real mp3 file.")
        logger.info(f"Arquivo de formato inválido gerado: {path}")
    except Exception as e:
        logger.error(f"Erro ao gerar arquivo inválido: {e}")

if __name__ == "__main__":
    success = generate_audio()
    if not success:
        exit(1)
