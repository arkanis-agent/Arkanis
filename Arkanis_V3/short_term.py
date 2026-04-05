import gc

def optimize_memory_usage() -> int:
    """Força a coleta de lixo e retorna a quantidade de objetos coletados."""
    return gc.collect()