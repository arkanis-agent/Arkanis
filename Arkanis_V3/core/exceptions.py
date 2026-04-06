Here's the merged content with the improvements incorporated while maintaining all existing functionality:

```python
class NetworkException(Exception):
    """Base para todos os erros de rede no sistema.
    
    Attributes:
        message (str): Mensagem human-readable do erro
        code (int): Código de erro HTTP padrão (default: 500)
        details (dict): Informações técnicas adicionais para debug
    
    Example:
        >>> raise NetworkException('Falha na conexão', code=503, details={'port': 8080})
    
    Exceção base para erros relacionados à rede.
    Esta exceção deve ser lançada quando ocorrer um problema de comunicação
    na rede, como falha de conexão, timeout, erro de protocolo, etc.
    """
    def __init__(self, message, code=500, details=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class NetworkTimeout(NetworkException):
    """Erro específico para timeouts de rede.
    
    Attributes:
        endpoint (str): URL ou endereço do endpoint
        timeout (float): Tempo limite em segundos
    
    Example:
        >>> raise NetworkTimeout('https://api.example.com', 30.0)
    """
    def __init__(self, endpoint, timeout):
        super().__init__(
            f"Timeout ao conectar em {endpoint} após {timeout}s",
            code=504,
            details={"endpoint": endpoint, "timeout": timeout}
        )

class SystemCritical(Exception):
    """Exceção para falhas críticas que exigem reinício imediato.
    
    Attributes:
        message (str): Mensagem human-readable do erro
        component (str): Nome do componente que falhou
        severity (int): Nível de severidade (1-5, sendo 5 o mais crítico)
    
    Example:
        >>> raise SystemCritical('Falha no subsistema', 'storage', severity=5)
    
    Exceção para falhas críticas que exigem reinício do sistema.
    Esta exceção deve ser lançada quando ocorrer um erro grave que comprometa
    o funcionamento do sistema e requeira um reinício para recuperação.
    """
    def __init__(self, message, component, severity=5):
        super().__init__(message)
        self.message = message
        self.component = component
        self.severity = severity

class DatabaseFailure(SystemCritical):
    """Falha crítica no banco de dados.
    
    Attributes:
        db_name (str): Nome do banco de dados que falhou
    
    Example:
        >>> raise DatabaseFailure('user_db')
    """
    def __init__(self, db_name):
        super().__init__(
            f"Falha crítica no banco de dados {db_name}",
            component="database",
            severity=5
        )
```