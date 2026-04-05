def validate_task_schema(task):
    required_fields = {
        'id': {'type': str, 'min_length': 1},
        'action': {'type': str, 'allowed': ['process', 'analyze', 'report']},
        'params': {'type': dict}
    }
    
    # Verifica campos obrigatórios
    if not all(field in task for field in required_fields):
        return False
    
    # Valida tipos e regras específicas
    for field, rules in required_fields.items():
        value = task[field]
        if not isinstance(value, rules['type']):
            return False
        
        if 'min_length' in rules and len(value) < rules['min_length']:
            return False
            
        if 'allowed' in rules and value not in rules['allowed']:
            return False
    
    return True

class InvalidTaskError(Exception):
    def __init__(self, message="Invalid task structure", errors=None):
        super().__init__(message)
        self.errors = errors or []