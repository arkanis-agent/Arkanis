import gc
import logging

logger = logging.getLogger(__name__)


def optimize_memory_usage(generation: int = -1) -> int:
    """Força a coleta de lixo e retorna a quantidade de objetos coletados.

    Args:
        generation: Geração do GC para coletar (0, 1, 2) ou -1 para todas (padrão).

    Returns:
        int: Número de objetos inacessíveis coletados.
    
    Note:
        O Python gerencia memória automaticamente. Use esta função apenas em
        contextos específicos (ex: pós-processamento de grandes datasets ou antes
        de operações críticas de memória)."""
    collected = gc.collect(generation)
    logger.debug("GC collected %d object(s) in generation %d.", collected, generation)
    return collected