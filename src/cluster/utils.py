def get_attrs_or_key(obj, key):
    if hasattr(obj, key):
        return getattr(obj, key)
    else:
        return obj[key]