# Imports adicionados
import ast
import hashlib

# Constantes de segurança adicionadas
SAFE_WRITE_TIMEOUT = 30
MAX_FILE_SIZE = 1024 * 1024  # 1MB

# ... (mantém o resto do código anterior igual) ...

def validate_path_safety(file_path):
    """Valida se o caminho está dentro do PROJECT_ROOT."""
    try:
        resolved = os.path.realpath(file_path)
        project_resolved = os.path.realpath(PROJECT_ROOT)
        
        if not resolved.startswith(project_resolved + os.sep) and resolved != project_resolved:
            logger.error(f"Path traversal detected: {file_path}")
            return False
        return True
    except Exception as e:
        logger.error(f"Path validation failed: {e}")
        return False

def validate_python_syntax(code):
    """Valida se o código é Python sintaticamente válido."""
    try:
        ast.parse(code)
        return True
    except SyntaxError as e:
        logger.error(f"Invalid Python syntax: {e}")
        return False

def apply_code(file_path, code, dry_write=False):
    """Aplica o código proposto ao arquivo com validações de segurança."""
    if not validate_path_safety(file_path):
        return False
    
    if not validate_python_syntax(code):
        logger.error(f"Rejected invalid Python code for {file_path}")
        return False
    
    if len(code) > MAX_FILE_SIZE:
        logger.error(f"Code exceeds MAX_FILE_SIZE limit for {file_path}")
        return False
    
    # Cria backup antes de modificar
    backup_path = None
    if os.path.exists(file_path) and not dry_write:
        backup_path = f"{file_path}.backup.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        with open(file_path, "r", encoding="utf-8") as f:
            with open(backup_path, "w", encoding="utf-8") as bf:
                bf.write(f.read())
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        return True
    except Exception as e:
        logger.error(f"Failed to write to {file_path}: {e}")
        if backup_path and not dry_write:
            rollback(file_path)
        return False

def rollback(file_path):
    """Usa git para rollback ou restaura do backup se disponível."""
    try:
        subprocess.run(["git", "checkout", "--", file_path], cwd=PROJECT_ROOT, check=True)
        logger.warning(f"Git rollback successful for {file_path}")
        return True
    except Exception:
        pass
    
    # Fallback para backup local se git falhar
    backup_files = glob.glob(f"{file_path}.backup.*")
    if backup_files:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                with open(sorted(backup_files)[-1], "r", encoding="utf-8") as bf:
                    f.write(bf.read())
            logger.warning(f"Local backup rollback for {file_path}")
            return True
        except Exception as e:
            logger.error(f"Backup rollback failed {file_path}: {e}")
    
    logger.error(f"Rollback FAILED for {file_path}")
    return False

# ... (mantém restantedo código igual incluindo import glob ao topo) ...
