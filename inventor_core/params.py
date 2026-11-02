"""Работа с параметрами детали. Без UI."""
from .com_helpers import iterate_collection


def list_parameters(part_doc):
    if part_doc is None:
        return []
    params = part_doc.ComponentDefinition.Parameters
    result = []
    for p in iterate_collection(params):
        result.append({
            "name": p.Name,
            "value_cm": p.Value,
            "value_mm": p.Value * 10,
            "units": p.Units,
            "comment": (p.Comment or ""),
        })
    return result


def set_parameter_mm(part_doc, name, value_mm):
    if part_doc is None:
        raise ValueError("Документ не передан")
    params = part_doc.ComponentDefinition.Parameters
    for p in iterate_collection(params):
        if p.Name == name:
            p.Value = value_mm / 10.0
            part_doc.Update()
            return True
    return False