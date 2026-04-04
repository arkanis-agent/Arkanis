def validate_task_schema(task):
    required_fields = ['id', 'action', 'params']
    return all(field in task for field in required_fields)

class InvalidTaskError(Exception):
    pass