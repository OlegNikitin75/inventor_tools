"""Подключение к Inventor и получение документов."""
import win32com.client

# Коды типов документов Inventor API.
# Проверены на реальных файлах:
#   5.ipt -> 12290 (деталь)
#   5.idw -> 12292 (чертёж)
#   12291  -> сборка (.iam)
PART_DOCUMENT = 12290
ASSEMBLY_DOCUMENT = 12291
DRAWING_DOCUMENT = 12292


def connect():
    """Подключиться к УЖЕ запущенному Inventor."""
    return win32com.client.Dispatch("Inventor.Application")


def get_active_part(app):
    """Активная деталь или None (если активен не .ipt)."""
    doc = app.ActiveDocument
    if doc is None:
        return None
    if doc.DocumentType != PART_DOCUMENT:
        return None
    return doc