# Melhorias: Imports explícitos e definição de API pública
# Evita colisão de nomes e melhora a legibilidade
from python_multipart.multipart import parse_multipart, FormData

__all__ = ['parse_multipart', 'FormData']