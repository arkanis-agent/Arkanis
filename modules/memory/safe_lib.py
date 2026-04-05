class SafeMemoryManager:
    def __init__(self):
        self.memory = {}
        self._next_address = 0

    def allocate(self, size: int) -> str:
        # Validação de segurança: size deve ser um inteiro positivo
        if not isinstance(size, int) or size <= 0:
            raise ValueError("Tamanho de alocação deve ser um inteiro positivo.")

        # Gerar endereço simulado
        address = f"0x{self._next_address:08X}"
        
        # Alocação segura (inicializa com zeros para evitar dados residuais)
        self.memory[address] = bytearray(size)
        
        # Incrementa o contador de endereço
        self._next_address += 1
        
        return address