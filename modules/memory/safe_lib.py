from typing import Dict

class SafeMemoryManager:
    """Gerenciador de Memória Segura para simulação de alocação de memória.

    Args:
        max_memory_bytes (int): Limite máximo de memória simulada em bytes.
    """

    def __init__(self, max_memory_bytes: int = 64 * 1024 * 1024):
        self.memory: Dict[str, bytearray] = {}
        self._next_address: int = 0
        self._allocated_total: int = 0
        self._max_memory: int = max_memory_bytes

    def allocate(self, size: int) -> str:
        """Aloca um bloco de memória simulada.

        Args:
            size (int): Tamanho do bloco de memória a ser alocado.

        Returns:
            str: Endereço simulado do bloco alocado.

        Raises:
            ValueError: Se o tamanho não for um inteiro positivo.
            MemoryError: Se o limite de memória for excedido.
        """
        if not isinstance(size, int) or size <= 0:
            raise ValueError("Tamanho de alocação deve ser um inteiro positivo.")

        if self._allocated_total + size > self._max_memory:
            raise MemoryError("Limite de memória simulada excedido.")

        address = f"0x{self._next_address:08X}"
        self.memory[address] = bytearray(size)

        self._next_address += size
        self._allocated_total += size

        return address