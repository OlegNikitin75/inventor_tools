# `inventor_connect.py`

Подключение к Inventor через COM и получение активного документа.

---

## 🎯 Зачем нужен этот модуль

Любой скрипт, работающий с Inventor, начинается одинаково:

1. подключиться к **уже запущенному** Inventor;
2. получить **активный документ**;
3. проверить, что это документ нужного типа (деталь, сборка, чертёж).

Если писать это в каждом скрипте — получается копипаста, в которой легко
ошибиться: забыть проверить `DocumentType`, перепутать числовой код,
уронить программу на `None`. Модуль собирает эту возню в три маленькие
функции и несколько именованных констант.

---

## 🔢 Константы типов документов

Inventor API возвращает тип документа **числом**. Числа «магические» —
их легко перепутать, поэтому они вынесены в именованные константы.

| Константа           | Значение | Расширение | Что это |
| ------------------- | -------- | ---------- | ------- |
| `PART_DOCUMENT`     | `12290`  | `.ipt`     | Деталь  |
| `ASSEMBLY_DOCUMENT` | `12291`  | `.iam`     | Сборка  |
| `DRAWING_DOCUMENT`  | `12292`  | `.idw`     | Чертёж  |

> Коды проверены на реальных файлах: `5.ipt → 12290`, `5.idw → 12292`,
> `12291 → .iam`.

**Пример:**

```python
from inventor_connect import PART_DOCUMENT, get_active_part

doc = get_active_part(app)
if doc is not None:
    # это точно .ipt
    ...
```

---

## 📦 API

### `connect()`

Подключается к **уже запущенному** Inventor.

**Возвращает:** COM-объект `Inventor.Application`.

**Пример:**

```python
from inventor_connect import connect

app = connect()
```

**Notes:** функция использует `Dispatch("Inventor.Application")` — это
подключение к работающему экземпляру. Если Inventor не запущен, поведение
зависит от настроек COM (обычно `Dispatch` попытается запустить новый
экземпляр или бросит исключение). Если нужен строго «уже запущенный» —
используйте `GetActiveObject` вместо `Dispatch`.

---

### `get_active_part(app)`

Возвращает активную деталь или `None`, если активен не `.ipt`.

| Параметр | Тип                    | Описание                                    |
| -------- | ---------------------- | ------------------------------------------- |
| `app`    | `Inventor.Application` | COM-объект Inventor (результат `connect()`) |

**Возвращает:** `Document` (деталь) или `None`.

**Пример:**

```python
from inventor_connect import connect, get_active_part

app = connect()
part = get_active_part(app)

if part is None:
    print("Активен не .ipt — откройте деталь и повторите.")
else:
    print(f"Активная деталь: {part.DisplayName}")
```

**Notes:** функция проверяет `DocumentType` и возвращает `None`, если:

- активного документа нет (`app.ActiveDocument is None`);
- активен документ другого типа (сборка, чертёж).

Это избавляет от `AttributeError` ниже по коду: вызывающий сразу видит
`None` и решает, что делать.

---

## 📖 Разбор по строкам

```python
"""Подключение к Inventor и получение документов."""
import win32com.client
```

Импорт `win32com.client` — это мост Python ↔ COM. Через него мы получаем
объект `Inventor.Application`, а дальше уже работаем с его свойствами и
методами как с обычным Python-объектом.

```python
PART_DOCUMENT = 12290
ASSEMBLY_DOCUMENT = 12291
DRAWING_DOCUMENT = 12292
```

Коды типов документов Inventor API. Вынесены в константы, чтобы в коде
было `doc.DocumentType != PART_DOCUMENT`, а не `!= 12290` — читается
сразу, а не «а что такое 12290?».

```python
def connect():
    """Подключиться к УЖЕ запущенному Inventor."""
    return win32com.client.Dispatch("Inventor.Application")
```

`Dispatch("Inventor.Application")` создаёт COM-объект по
ProgID. Возвращаем его наружу — все дальнейшие вызовы идут через `app`.

```python
def get_active_part(app):
    """Активная деталь или None (если активен не .ipt)."""
    doc = app.ActiveDocument
```

Берём активный документ. Если Inventor только что запустился и ничего не
открыто — `ActiveDocument` будет `None`.

```python
    if doc is None:
        return None
```

Нет активного документа — возвращаем `None`. Без этой проверки следующая
строка `doc.DocumentType` упала бы с `AttributeError`.

```python
    if doc.DocumentType != PART_DOCUMENT:
        return None
    return doc
```

Если активен не `.ipt` (сборка, чертёж) — тоже `None`. Иначе возвращаем
документ. Теперь вызывающий код может писать:

```python
part = get_active_part(app)
if part is None:
    ...
```

и не бояться, что внутри что-то упадёт.

---

## 💡 Пример использования целиком

```python
from inventor_connect import connect, get_active_part

def main():
    app = connect()
    part = get_active_part(app)

    if part is None:
        print("Откройте деталь (.ipt) и запустите снова.")
        return

    print(f"Работаем с деталью: {part.DisplayName}")
    # ... дальше — работа с part ...

if __name__ == "__main__":
    main()
```

---

## ✅ Что даёт модуль

- **Именованные константы** вместо «магических» чисел `12290/12291/12292`.
- **Безопасное получение активной детали** — не падает на `None` и на
  документах другого типа.
- **Единая точка подключения** — если завтра понадобится `GetActiveObject`
  вместо `Dispatch`, правится в одном месте.
