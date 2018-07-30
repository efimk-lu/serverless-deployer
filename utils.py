from typing import Iterable, Any, Optional


def nested_get(input_dict: dict, nested_key: Iterable[Any]) -> Optional[Any]:
    """
    Retrieve value from nested dictionary, e.g. test['hello]['my']['friend'] if not found return None
    """
    internal_dict_value = input_dict
    for k in nested_key:
        internal_dict_value = internal_dict_value.get(k, None)
        if internal_dict_value is None:
            return None
    return internal_dict_value
