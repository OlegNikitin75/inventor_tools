# `inventor_export.py`

Пакетный экспорт документов Inventor: **STEP для 3D-моделей**, **PDF для
чертежей**. Без UI.

---

## 🎯 Зачем нужен этот модуль

Рутинная задача: есть папка с документами Inventor — надо получить рядом
папку с результатами:

- **`.ipt` / `.iam`** (детали и сборки) → **`.stp`** (STEP);
- **`.idw` / `.dwg`** (чертежи) → **`.pdf`** (PDF).

Делать это руками через «Сохранить как…» долго. Модуль делает это
программно:

- находит в папке файлы нужных типов;
- открывает каждый **без показа окна**;
- экспортирует через `Document.SaveAs(path, SaveCopyAs=True)` —
  Inventor сам выбирает транслятор по расширению файла;
- закрывает документ и идёт к следующему;
- считает успехи и ошибки, пишет лог.

---

## ⚠️ Ключевое разделение: STEP ≠ PDF

**PDF-аддин Inventor предназначен для чертежей.** У чертежа есть листы,
рамки, штампы — PDF-транслятор знает, как их компоновать. Деталь или
сборка — это 3D-модель без «страницы», и PDF-аддин не знает, что с ней
делать. Поэтому:

| Тип документа | Расширения | Куда экспортируем |
|---|---|---|
| 3D-модель | `.ipt`, `.iam` | `.stp` (STEP) |
| Чертёж | `.idw`, `.dwg` | `.pdf` (PDF) |

Попытка экспортировать `.ipt`/`.iam` в PDF через PDF-аддин — источник
ошибок и падений. Модуль этого не делает: каждый тип идёт своим путём.

---

## 🔧 Почему `doc.SaveAs`, а не `TranslatorAddIn.SaveCopyAs`

Изначально экспорт был сделан через аддины:

```python
addin = app.ApplicationAddIns.ItemById(STEP_ADDIN_ID)
ctx = app.TransientObjects.CreateTranslationContext()
opts = app.TransientObjects.CreateNameValueMap()
data = app.TransientObjects.CreateDataMedium()
data.FileName = out_path
addin.SaveCopyAs(doc, ctx, opts, data)
```

На практике это **нестабильно в `win32com`**: `ItemById` возвращает
`ApplicationAddIn`, у которого нет методов `HasSaveCopyAsOptions` и
`SaveCopyAs`. Приведение типов через `CastTo` / `Dispatch` помогает не
во всех версиях Inventor и Python. Типичная ошибка:

```
(-2147352567, 'Ошибка.', (0, None, None, None, 0, -2147418113), None)
```

**Решение — `doc.SaveAs(path, True)`.** Второй аргумент `True` означает
`SaveCopyAs`: исходный документ не меняется, а Inventor сам выбирает
транслятор по расширению файла. Это надёжнее и проще.

**Компромисс:** нельзя передать специфические опции (например, протокол
STEP AP214 или «все листы PDF в один файл»). Для базового экспорта этого
достаточно. Если опции понадобятся — придётся вернуться к
`TranslatorAddIn` с `Activate()` и настройкой `opts`.

---

## 📦 API

### `export_models_to_step(app, input_dir, output_dir, log=print)`

Экспортирует все `.ipt` / `.iam` из `input_dir` в `.stp`.

| Параметр | Тип | Описание |
|---|---|---|
| `app` | `Inventor.Application` | COM-объект Inventor |
| `input_dir` | `str` | Папка с моделями |
| `output_dir` | `str` | Папка результатов (создаётся) |
| `log` | `callable` | Функция логирования |

**Возвращает:** `tuple[int, int]` — `(ok, fail)`.

**Пример:**

```python
from inventor_connect import connect
from inventor_export import export_models_to_step

app = connect()
ok, fail = export_models_to_step(
    app,
    input_dir=r"C:\Projects\Models",
    output_dir=r"C:\Projects\Export",
)
```

---

### `export_drawings_to_pdf(app, input_dir, output_dir, log=print)`

Экспортирует все `.idw` / `.dwg` из `input_dir` в `.pdf`.

Параметры и возврат — как у `export_models_to_step`.

**Пример:**

```python
from inventor_connect import connect
from inventor_export import export_drawings_to_pdf

app = connect()
ok, fail = export_drawings_to_pdf(
    app,
    input_dir=r"C:\Projects\Drawings",
    output_dir=r"C:\Projects\Export",
)
```

---

### `run_export(app, input_dir, output_dir, do_step=True, do_pdf=True, log=print)`

Удобная обёртка: запускает оба экспорта подряд.

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `app` | `Inventor.Application` | — | COM-объект Inventor |
| `input_dir` | `str` | — | Папка с исходниками |
| `output_dir` | `str` | — | Папка результатов |
| `do_step` | `bool` | `True` | Экспортировать модели в STEP |
| `do_pdf` | `bool` | `True` | Экспортировать чертежи в PDF |
| `log` | `callable` | `print` | Функция логирования |

**Возвращает:** `tuple[int, int]` — суммарно `(ok, fail)`.

**Пример:**

```python
from inventor_connect import connect
from inventor_export import run_export

app = connect()
ok, fail = run_export(
    app,
    input_dir=r"C:\Projects\All",
    output_dir=r"C:\Projects\Export",
)
print(f"Успешно: {ok}, с ошибками: {fail}")
```

---

## 📖 Как это работает

### `_iter_files(input_dir, extensions)`

Внутренняя функция: собирает файлы из `input_dir` с нужными
расширениями. `os.path.splitext(fname)[1].lower()` — чтобы поймать
`.IPT`, `.IAM` и т.п.

### `export_models_to_step` / `export_drawings_to_pdf`

Обе функции устроены одинаково:

1. `os.makedirs(output_dir, exist_ok=True)` — создаём папку результата.
2. `_iter_files(input_dir, ...)` — собираем файлы нужных расширений.
3. Цикл по файлам:
   - `app.Documents.Open(full, False)` — открываем **без окна**
     (второй аргумент `False`);
   - `doc.SaveAs(out, True)` — экспорт с `SaveCopyAs=True`;
   - `ok += 1` при успехе;
   - при исключении — `log(f"   ОШИБКА: {e}")`, `fail += 1`, цикл идёт
     дальше (один битый файл не роняет пакет);
   - `finally: doc.Close(True)` — закрываем документ **в любом случае**.

### `run_export`

Просто вызывает `export_models_to_step` и/или `export_drawings_to_pdf` в
зависимости от флагов `do_step` / `do_pdf` и суммирует счётчики.

---

## 💡 Пример: свой лог в файл

```python
from inventor_connect import connect
from inventor_export import run_export

def main():
    app = connect()

    lines = []
    def log(msg):
        print(msg)
        lines.append(msg)

    ok, fail = run_export(
        app,
        input_dir=r"C:\Projects\All",
        output_dir=r"C:\Projects\Export",
        log=log,
    )

    with open(r"C:\Projects\Export\export.log", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Готово: {ok} ок, {fail} ошибок")

if __name__ == "__main__":
    main()
```

---

## 🔧 Настройки экспорта (если понадобятся)

Сейчас `doc.SaveAs(out, True)` не даёт доступа к опциям транслятора.
Если понадобятся:

- **STEP: протокол AP214** — вернуться к `TranslatorAddIn`, вызвать
  `addin.Activate()`, затем `opts.Value["ApplicationProtocol"] = "AP214IS"`.
- **PDF: чёрно-белый, разрешение, все листы в один файл** — аналогично,
  через `opts.Value[...]` перед `SaveCopyAs`.

Имена ключей зависят от версии Inventor — подсматривать в документации
или экспериментально.

> ⚠️ В некоторых версиях Inventor (например, 2018) вызов
> `HasSaveCopyAsOptions` для PDF приводил к сбою. Если столкнётесь —
> можно обойтись без проверки: сразу вызывать `SaveCopyAs` после
> `Activate()`.

---

## ✅ Что даёт модуль

- **Правильное разделение форматов** — STEP для моделей, PDF для чертежей.
- **Надёжный экспорт** — `doc.SaveAs` вместо капризного
  `TranslatorAddIn.SaveCopyAs`.
- **Пакетная обработка** — вся папка за один запуск.
- **Без UI** — документы открываются в фоне.
- **Устойчивость** — один битый файл не роняет пакет.
- **Лог** — видно, что получилось, а что нет.
- **Две отдельные функции** — можно вызывать по отдельности, если нужен
  только STEP или только PDF.