class ArkanisException(Exception):
    """Exceção base para todos os erros do sistema Arkanis V3."""
    def __init__(self, message: str, code: int = 500, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class MultipartException(ArkanisException):
    """Exceção base para erros de multipart (form-data/file uploads)."""
    def __init__(self, message: str, code: int = 400, details: dict = None):
        super().__init__(message, code, details)


class MultipartSizeExceeded(MultipartException):
    """Exceção lançada quando o tamanho do multipart excede o limite."""
    def __init__(self, size: int, max_size: int):
        super().__init__(
            message=f"Tamanho do multipart ({size} bytes) excede o limite ({max_size} bytes)",
            code=413,
            details={"received": size, "max": max_size}
        )


class MultipartParseError(MultipartException):
    """Exceção para erros durante o parsing do multipart."""
    def __init__(self, message: str, position: int = None):
        details = {"position": position} if position else {}
        super().__init__(
            message=message,
            code=400,
            details=details
        )


class MultipartContentTypeError(MultipartException):
    """Exceção quando o Content-Type não é multipart."""
    def __init__(self, expected: str, received: str):
        super().__init__(
            message=f"Content-Type inválido. Esperado: {expected}. Recebido: {received}",
            code=415,
            details={"expected": expected, "received": received}
        )


__all__ = [
    "ArkanisException",
    "MultipartException",
    "MultipartSizeExceeded",
    "MultipartParseError",
    "MultipartContentTypeError",
]