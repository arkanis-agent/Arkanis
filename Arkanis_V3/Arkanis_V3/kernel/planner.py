import re
import json

def _parse_plan(raw_input: str) -> list[dict]:
    """Parses raw input containing JSON plans with robust error handling.
    
    Args:
        raw_input: String potentially containing one or more JSON objects.
        
    Returns:
        List of parsed JSON dictionaries.
        
    Raises:
        ValueError: If no valid JSON structure is found after exhaustive attempts.
    """
    # Pre-process: Normalize line breaks and remove common noise patterns
    normalized = re.sub(r'^[^{]*', '', raw_input, flags=re.DOTALL)
    normalized = re.sub(r'[^}]*$', '', normalized, flags=re.DOTALL)
    
    # Attempt 1: Strict JSON parsing
    try:
        return json.loads(normalized)
    except json.JSONDecodeError:
        pass
        
    # Attempt 2: Extract all potential JSON blocks
    json_blocks = re.findall(r'\{[^{}]*\}', normalized)
    
    valid_plans = []
    for block in json_blocks:
        try:
            plan = json.loads(block)
            if isinstance(plan, dict):
                valid_plans.append(plan)
        except json.JSONDecodeError:
            continue
    
    if valid_plans:
        return valid_plans
        
    # Final attempt: Lenient parsing with error recovery
    try:
        return json.loads(normalized.replace("'", '"'))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse plan from input. Error: {str(e)}\n"
            f"Input was: {raw_input[:200]}..."
        )