# `part_parameters.py`

Работа с параметрами детали Inventor: чтение списка и установка значения.
Без UI.

---

## 🎯 Зачем нужен этот модуль

У детали Inventor есть **параметры** (Parameters) — именованные величины,
которыми управляют геометрией: длины, углы, допуски. Через COM они
доступны как коллекция, но с тремя неудобствами:

1. **Значения в сантиметрах.** Inventor API хранит длины в сантиметрах,
   а в UI показывает в миллиметрах. Легко забыть про множитель 10.
2. **Индексация с 1.** Как и любая COM-коллекция, `Parameters` требует
   `Item(1)`, а не `[0]` — см. `com_helpers.iterate_collection`.
3. **Повтор в каждом скрипте.** Обход параметров и поиск по имени — одна
   и та же копипаста.

Модуль даёт две функции: **прочитать все параметры** в удобном виде и
**установить значение по имени** в миллиметрах.

---

## 🔢 Единицы: сантиметры в API, миллиметры в UI

Inventor API всегда возвращает и принимает длины **в сантиметрах**,
независимо от того, что показывает UI. Поэтому:

- `p.Value` — это сантиметры;
- чтобы получить миллиметры — умножить на 10;
- чтобы задать миллиметры — разделить на 10.

Модуль делает это преобразование сам: `list_parameters` возвращает и
`value_cm`, и `value_mm`, а `set_parameter_mm` принимает миллиметры.

> ⚠️ Это верно только для **длин**. Углы хранятся в радианах, и
> множитель 10 к ним не применяется. Если понадобятся углы — нужно
> отдельное преобразование.

---

## 📦 API

### `list_parameters(part_doc)`

Возвращает список параметров детали в виде словарей.

| Параметр | Тип | Описание |
|---|---|---|
| `part_doc` | `Document` или `None` | Документ детали (`.ipt`) |

**Возвращает:** `list[dict]`. Каждый словарь содержит:

| Ключ | Тип | Что это |
|---|---|---|
| `name` | `str` | Имя параметра (например, `"Длина"`, `"d1"`) |
| `value_cm` | `float` | Значение в сантиметрах (как в API) |
| `value_mm` | `float` | Значение в миллиметрах (как в UI) |
| `units` | `str` | Единицы измерения (например, `"mm"`, `"deg"`) |
| `comment` | `str` | Комментарий (пустая строка, если нет) |

Если `part_doc is None` — возвращает пустой список.

**Пример:**

```python
from inventor_connect import connect, get_active_part
from part_parameters import list_parameters

app = connect()
part = get_active_part(app)

for p in list_parameters(part):
    print(f"{p['name']}: {p['value_mm']:.2f} {p['units']}")
```

**Пример вывода:**

```
Длина: 150.00 mm
Ширина: 80.00 mm
Угол: 45.00 deg
```

---

### `set_parameter_mm(part_doc, name, value_mm)`

Устанавливает значение параметра по имени, в миллиметрах.

| Параметр | Тип | Описание |
|---|---|---|
| `part_doc` | `Document` | Документ детали (`.ipt`) |
| `name` | `str` | Имя параметра |
| `value_mm` | `float` | Новое значение в миллиметрах |

**Возвращает:** `bool` — `True`, если параметр найден и обновлён;
`False`, если параметра с таким именем нет.

**Бросает:** `ValueError`, если `part_doc is None`.

**Пример:**

```python
from inventor_connect import connect, get_active_part
from part_parameters import set_parameter_mm

app = connect()
part = get_active_part(app)

if set_parameter_mm(part, "Длина", 200.0):
    print("Параметр обновлён")
else:
    print("Параметр не найден")
```

**Notes:** после установки значения вызывается `part_doc.Update()` —
Inventor перестраивает геометрию. Без этого изменения могут не примениться
до следующего ручного обновления.

---

## 📖 Разбор по строкам

### `list_parameters`

```python
def list_parameters(part_doc):
    if part_doc is None:
        return []
```

Защита от `None`: если документ не передан или активен не `.ipt` —
возвращаем пустой список. Без этого следующая строка упала бы с
`AttributeError`.

```python
    params = part_doc.ComponentDefinition.Parameters
```

`Parameters` — коллекция параметров компонента. У детали она есть всегда
(даже если параметров нет — будет пустая коллекция).

```python
    result = []
    for p in iterate_collection(params):
```

`iterate_collection` из `com_helpers` прячет 1-индексацию и проверку на
`None` — см. документацию `com_helpers.md`.

```python
        result.append({
            "name": p.Name,
            "value_cm": p.Value,
            "value_mm": p.Value * 10,
            "units": p.Units,
            "comment": (p.Comment or ""),
        })
```

Собираем словарь по каждому параметру:

- `p.Value` — сантиметры (как в API);
- `p.Value * 10` — миллиметры (как в UI);
- `p.Units` — единицы (`"mm"`, `"deg"`, `"in"` и т.п.);
- `(p.Comment or "")` — `Comment` может быть `None`, приводим к пустой
  строке, чтобы не ловить `None` в вызывающем коде.

### `set_parameter_mm`

```python
def set_parameter_mm(part_doc, name, value_mm):
    if part_doc is None:
        raise ValueError("Документ не передан")
```

Здесь `None` — это ошибка вызывающего: он явно просит установить
параметр, но не дал документ. Поэтому `ValueError`, а не молчаливый
`False`.

```python
    params = part_doc.ComponentDefinition.Parameters
    for p in iterate_collection(params):
        if p.Name == name:
            p.Value = value_mm / 10.0
```

Ищем параметр по имени. Нашли — переводим миллиметры в сантиметры
(`value_mm / 10.0`) и записываем в `p.Value`. API ждёт сантиметры.

```python
            part_doc.Update()
            return True
```

`Update()` перестраивает геометрию с учётом нового значения. Без него
изменение «повиснет» до следующего обновления. Возвращаем `True` — успех.

```python
    return False
```

Параметр с таким именем не найден. Возвращаем `False` — вызывающий сам
решит, что делать (лог, исключение, пропуск).

---

## 💡 Пример: изменить группу параметров и сохранить

```python
from inventor_connect import connect, get_active_part
from part_parameters import list_parameters, set_parameter_mm

def main():
    app = connect()
    part = get_active_part(app)

    if part is None:
        print("Откройте деталь (.ipt).")
        return

    print("Было:")
    for p in list_parameters(part):
        print(f"  {p['name']}: {p['value_mm']:.2f} {p['units']}")

    # Увеличить все длины на 10%
    for p in list_parameters(part):
        if p["units"] == "mm":
            set_parameter_mm(part, p["name"], p["value_mm"] * 1.1)

    print("Стало:")
    for p in list_parameters(part):
        print(f"  {p['name']}: {p['value_mm']:.2f} {p['units']}")

if __name__ == "__main__":
    main()
```

---

## ⚠️ Ограничения

- **Только длины.** Углы хранятся в радианах, и `* 10` / `/ 10` к ним
  применять нельзя. Если понадобятся — нужны отдельные функции
  `set_parameter_deg` / `set_parameter_rad`.
- **Только параметры компонента.** Параметры эскизов, деталей в сборке
  и т.п. лежат в других коллекциях — этот модуль их не трогает.
- **`Update()` на каждый параметр.** В примере выше `Update()`
  вызывается внутри `set_parameter_mm` на каждом вызове. Для многих
  параметров это медленно. Если нужно быстро — сделайте отдельную
  функцию `set_parameters_mm(part_doc, mapping)`, которая меняет все
  значения, а `Update()` вызывает один раз в конце.

---

## ✅ Что даёт модуль

- **Единицы не путаются** — сантиметры и миллиметры явно разделены.
- **1-индексация скрыта** — через `iterate_collection`.
- **`None`-безопасность** — `list_parameters(None)` не падает.
- **Понятный результат** — список словарей, а не COM-объекты.
- **Обновление геометрии** — `Update()` вызывается автоматически.