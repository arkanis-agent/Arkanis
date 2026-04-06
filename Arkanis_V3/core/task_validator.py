def validate_task_schema(task):
    required_fields = {
        'id': {'type': str, 'min_length': 1},
        'action': {'type': str, 'allowed': ['process', 'analyze', 'report']},
        'params': {'type': dict, 'required_keys': ['source', 'priority']}
    }
    
    errors = []
    
    # Verifica campos obrigatórios
    missing_fields = [field for field in required_fields if field not in task]
    if missing_fields:
        errors.append(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Valida tipos e regras específicas
    for field, rules in required_fields.items():
        if field not in task:
            continue
            
        value = task[field]
        if not isinstance(value, rules['type']):
            errors.append(f"Field '{field}' must be of type {rules['type'].__name__}")
            continue
            
        if 'min_length' in rules and len(value) < rules['min_length']:
            errors.append(f"Field '{field}' must have at least {rules['min_length']} characters")
            
        if 'allowed' in rules and value not in rules['allowed']:
            allowed_values = ', '.join(rules['allowed'])
            errors.append(f"Field '{field}' must be one of: {allowed_values}")
            
        if field == 'params' and 'required_keys' in rules:
            missing_params = [key for key in rules['required_keys'] if key not in value]
            if missing_params:
                errors.append(f"Params missing required keys: {', '.join(missing_params)}")
    
    if errors:
        raise InvalidTaskError(errors=errors)
    
    return True

class InvalidTaskError(Exception):
    def __init__(self, message="Invalid task structure", errors=None):
        super().__init__(message)
        self.errors = errors or []
    
    def __str__(self):
        base_msg = super().__str__()
        if not self.errors:
            return base_msg
        return f"{base_msg}\nErrors:\n- " + "\n- ".join(self.errors)