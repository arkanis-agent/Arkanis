class NetworkException(Exception):
    """Exceção base para erros de rede"""
    pass

class SystemCritical(Exception):
    """Exceção para falhas críticas que exigem reinício"""
    pass