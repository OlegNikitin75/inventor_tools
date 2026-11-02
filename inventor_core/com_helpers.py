"""Обёртки над COM-коллекциями Inventor."""

def iterate_collection(collection):
    if collection is None:
        return
    for i in range(1, collection.Count + 1):
        yield collection.Item(i)


def safe_get(obj, name, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default