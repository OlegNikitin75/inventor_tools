# `export_worker.py`

Фоновый поток для экспорта документов Inventor. Обёртка над
`inventor_core.export.run_export`, которая не блокирует UI и отдаёт
прогресс через Qt-сигналы.

---

## 🎯 Зачем нужен этот модуль

Экспорт папки с моделями и чертежами — **долгая операция**. Inventor
открывает каждый файл, транслирует его, закрывает — на десятках файлов
это минуты. Если запустить это прямо в обработчике кнопки, UI замрёт:

- окно не перерисовывается;
- кнопки не нажимаются;
- пользователь думает, что программа зависла.

Решение — **вынести экспорт в отдельный поток**. Модуль оборачивает
`run_export` в `QThread` и даёт два сигнала:

- `log(str)` — каждая строка лога (что экспортируется, что упало);
- `done(int, int)` — итог: `(ok, fail)`, когда всё закончилось.

UI подключает эти сигналы к своим виджетам (текстовое поле для лога,
итоговая надпись, разблокировка кнопки) — и остаётся отзывчивым.

---

## 🧵 Что такое `QThread` и почему сигналы

`QThread` — класс Qt для работы в отдельном потоке. Его метод `run()`
выполняется **не в UI-потоке**, поэтому долгие операции в нём не морозят
интерфейс.

Важное правило Qt: **из фонового потока нельзя напрямую трогать
виджеты**. Вместо этого поток испускает **сигналы** (`Signal`), а UI
подписывается на них через `connect()`. Qt сам позаботится о том, чтобы
обработчик сигнала выполнился в UI-потоке.

Поэтому в `ExportWorker`:

- `log` и `done` — сигналы;
- в `run()` вызывается `self.log.emit(...)` и `self.done.emit(...)`,
  а не прямой вызов методов виджетов.

---

## 📦 API

### `class ExportWorker(QThread)`

Фоновый поток экспорта.

#### Сигналы

| Сигнал | Аргументы | Когда испускается |
|---|---|---|
| `log` | `str` | На каждую строку лога от `run_export` |
| `done` | `int, int` | Один раз, в конце: `(ok, fail)` |

#### `__init__(self, app, input_dir, output_dir, do_step, do_pdf)`

| Параметр | Тип | Описание |
|---|---|---|
| `app` | `Inventor.Application` | COM-объект Inventor |
| `input_dir` | `str` | Папка с исходниками |
| `output_dir` | `str` | Папка результатов |
| `do_step` | `bool` | Экспортировать модели в STEP |
| `do_pdf` | `bool` | Экспортировать чертежи в PDF |

Просто сохраняет параметры в `self`. Никакой работы здесь не делается —
всё в `run()`.

#### `run(self)`

Выполняется в фоновом потоке при вызове `worker.start()`.

Вызывает `run_export(...)` из `inventor_core.export`, передавая
`log=self.log.emit` — то есть каждая строка лога сразу уходит в сигнал.
В конце испускает `done(ok, fail)`.

**Возвращает:** ничего. Результат — через сигнал `done`.

---

## 💡 Пример использования

```python
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QLineEdit, QTextEdit, QLabel, QCheckBox, QFileDialog,
)
from inventor_connect import connect
from export_worker import ExportWorker


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.app = connect()
        self.worker = None

        self.input_edit = QLineEdit()
        self.output_edit = QLineEdit()
        self.step_check = QCheckBox("STEP")
        self.step_check.setChecked(True)
        self.pdf_check = QCheckBox("PDF")
        self.pdf_check.setChecked(True)

        self.run_btn = QPushButton("Экспортировать")
        self.run_btn.clicked.connect(self.start_export)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.status = QLabel("Готов")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Входная папка:"))
        layout.addWidget(self.input_edit)
        layout.addWidget(QLabel("Выходная папка:"))
        layout.addWidget(self.output_edit)
        layout.addWidget(self.step_check)
        layout.addWidget(self.pdf_check)
        layout.addWidget(self.run_btn)
        layout.addWidget(self.log_view)
        layout.addWidget(self.status)

    def start_export(self):
        if self.worker is not None and self.worker.isRunning():
            return

        self.run_btn.setEnabled(False)
        self.status.setText("Экспорт…")
        self.log_view.clear()

        self.worker = ExportWorker(
            self.app,
            self.input_edit.text(),
            self.output_edit.text(),
            self.step_check.isChecked(),
            self.pdf_check.isChecked(),
        )
        self.worker.log.connect(self.log_view.append)
        self.worker.done.connect(self.on_done)
        self.worker.start()

    def on_done(self, ok, fail):
        self.run_btn.setEnabled(True)
        self.status.setText(f"Готово: {ok} ок, {fail} ошибок")


if __name__ == "__main__":
    app = QApplication([])
    w = MainWindow()
    w.show()
    app.exec()
```

**Что происходит:**

1. Пользователь нажимает «Экспортировать» — кнопка блокируется, лог
   очищается.
2. Создаётся `ExportWorker`, подключаются сигналы, вызывается `start()`.
3. В фоновом потоке крутится `run_export`. Каждая строка лога приходит
   в `log_view.append` (в UI-потоке — Qt сам переключает).
4. Когда всё закончилось, приходит `done(ok, fail)` — кнопка
   разблокируется, статус обновляется.

UI всё это время отзывчив: окно перерисовывается, кнопки (кроме
заблокированной) работают.

---

## 📖 Разбор по строкам

```python
from PySide6.QtCore import QThread, Signal
from inventor_core.export import run_export
```

`QThread` — базовый класс потока, `Signal` — механизм сигналов Qt.
`run_export` — функция из `inventor_core.export`, которую мы оборачиваем.

```python
class ExportWorker(QThread):
    log = Signal(str)
    done = Signal(int, int)
```

Сигналы объявляются **на уровне класса** (так требует Qt). `log`
передаёт строку, `done` — два числа.

```python
    def __init__(self, app, input_dir, output_dir, do_step, do_pdf):
        super().__init__()
        self.app = app
        ...
```

Сохраняем параметры. `super().__init__()` — обязательный вызов
конструктора `QThread`.

```python
    def run(self):
        ok, fail = run_export(
            self.app, self.input_dir, self.output_dir,
            self.do_step, self.do_pdf,
            log=self.log.emit,
        )
        self.done.emit(ok, fail)
```

`run()` выполняется в фоновом потоке. Передаём `log=self.log.emit` —
`run_export` будет вызывать `self.log.emit("...")` на каждой строке,
и сигнал сразу уйдёт подписчикам. В конце — `done.emit(ok, fail)`.

**Обратите внимание:** `run()` не должен трогать виджеты. Только
`emit` сигналов — это безопасно из любого потока.

---

## ⚠️ Важные нюансы

### Нельзя переиспользовать один `ExportWorker`

`QThread` нельзя запустить повторно после завершения. На каждый экспорт
создавайте **новый** `ExportWorker`. В примере выше это учтено: в
`start_export` создаётся новый объект каждый раз.

### Нельзя убивать поток через `terminate()`

`QThread.terminate()` — аварийное завершение, которое может оставить
COM-объекты Inventor в неконсистентном состоянии. Если нужно прервать
экспорт — лучше добавить в `run_export` флаг отмены (например,
`threading.Event`), проверять его в цикле и аккуратно выходить.

### COM и потоки

Inventor — COM-объект. При работе с COM из фонового потока может
понадобиться инициализация COM в этом потоке:

```python
import pythoncom

def run(self):
    pythoncom.CoInitialize()
    try:
        ok, fail = run_export(...)
        self.done.emit(ok, fail)
    finally:
        pythoncom.CoUninitialize()
```

Если экспорт работает и без этого — хорошо. Если начнутся странные
ошибки COM (`CoInitialize has not been called`) — добавьте. Подробности
зависят от того, как `connect()` получает `app` и в каком потоке это
происходит.

### Один Inventor — один поток

Inventor не любит, когда его дёргают из нескольких потоков
одновременно. Пока `ExportWorker` работает, не запускайте другие
операции с тем же `app` из UI-потока. Если нужно — ставьте в очередь.

---

## ✅ Что даёт модуль

- **UI не зависает** — экспорт в фоне.
- **Прогресс в реальном времени** — каждая строка лога сразу в UI.
- **Итог** — `done(ok, fail)` для финального статуса.
- **Чистое разделение** — `inventor_core` ничего не знает про Qt,
  `export_worker` ничего не знает про виджеты.