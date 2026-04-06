"""Multipart handling module with automatic fallback to python_multipart.

This module provides convenient import for multipart parsing.
If a local multipart.py exists, it will be loaded first.
Otherwise, falls back to the python_multipart library.

Examples:
    >>> from multipart import parse_options_header
    >>> result = parse_options_header('Content-Disposition')
"""

import importlib.util
import logging
import sys
import warnings
from pathlib import Path
from typing import Any

# Configure logging for module
logger = logging.getLogger(__name__)

# Define explicit exports
__all__ = [
    'parse_options_header',
    'Parser',
    'HeadersParser',
    '__version__',
    '__author__',
    '__copyright__',
    '__license__',
]

# Try to load local multipart.py first, then fall back to library
_multipart_module: Any

try:
    for import_path in sys.path:
        file_path = Path(import_path) / 'multipart.py'
        if file_path.is_file():
            try:
                spec = importlib.util.spec_from_file_location('multipart', file_path)
                if spec is None or spec.loader is None:
                    raise RuntimeError(f"{file_path} found but not loadable")
                module = importlib.util.module_from_spec(spec)
                sys.modules['multipart'] = module
                spec.loader.exec_module(module)
                _multipart_module = module
                logger.info(f"Loaded multipart from: {file_path}")
                break
            except PermissionError:
                logger.debug(f"Permission denied: {file_path}")
                continue
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")
                continue
        else:
            logger.debug(f"No multipart.py found at: {file_path}")
    else:
        raise RuntimeError("No multipart.py found in sys.path")

except Exception as e:
    logger.warning(f"Local multipart not available: {e}, falling back to python_multipart")
    try:
        import python_multipart
        _multipart_module = python_multipart
    except ImportError as import_error:
        logger.error(f"python_multipart not installed: {import_error}")
        raise ImportError(
            "Please install python_multipart using: pip install python-multipart"
        ) from import_error

# Forward important attributes
__version__ = getattr(_multipart_module, '__version__', 'unknown')
__author__ = getattr(_multipart_module, '__author__', 'unknown')
__copyright__ = getattr(_multipart_module, '__copyright__', 'unknown')
__license__ = getattr(_multipart_module, '__license__', 'unknown')

# Forward all public API symbols explicitly
for attr_name in dir(_multipart_module):
    if attr_name.startswith('_') or attr_name not in __all__:
        continue
    if not attr_name.startswith('__') or attr_name not in ['__version__', '__author__', '__copyright__', '__license__']:
        if hasattr(_multipart_module, attr_name):
            globals()[attr_name] = getattr(_multipart_module, attr_name)
