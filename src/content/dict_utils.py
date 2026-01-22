"""Dictionary manipulation utilities."""

from typing import Dict, Any


def safe_get_nested(d: Dict, *keys, default=None) -> Any:
    """Safely get nested dictionary value.
    
    Args:
        d: Dictionary to query
        *keys: Sequence of keys to traverse
        default: Value to return if path doesn't exist
        
    Returns:
        Value at the nested path, or default if not found
        
    Example:
        >>> d = {'a': {'b': {'c': 1}}}
        >>> safe_get_nested(d, 'a', 'b', 'c')
        1
        >>> safe_get_nested(d, 'a', 'x', default=0)
        0
    """
    current = d
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
    return current if current is not None else default


def merge_dicts(*dicts: Dict) -> Dict:
    """Merge multiple dictionaries, later ones override earlier ones.
    
    Args:
        *dicts: Dictionaries to merge
        
    Returns:
        Merged dictionary
        
    Example:
        >>> merge_dicts({'a': 1}, {'b': 2}, {'a': 3})
        {'a': 3, 'b': 2}
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result
