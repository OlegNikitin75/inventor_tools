# `main_window.py`

Главное окно продукта «Массовый экспорт» на PySide6. Одна вкладка:
выбор папок, флаги STEP/PDF, кнопка запуска и лог.

---

## 🎯 Зачем нужен этот модуль

Это **точка входа в UI** продукта. Пользователь видит окно с одной
вкладкой «Массовый экспорт», где может:

1. выбрать входную папку (откуда брать `.ipt` / `.iam` / `.idw` / `.dwg`);
2. выбрать выходную папку (куда складывать `.stp` / `.pdf`);
3. включить/выключить экспорт в STEP и PDF;
4. нажать «Запустить» и смотреть лог в реальном времени.

Под капотом окно:

- проверяет, что папки указаны и входная существует;
- подключается к Inventor;
- запускает `ExportWorker` (фоновый поток) — см. `export_worker.md`;
- показывает лог и итоговый результат;
- блокирует кнопку на время экспорта, чтобы не запустить два потока
  одновременно.

Вся работа с Inventor — в `inventor_core`, виджеты — только в этом
модуле. Разделение чистое: UI ничего не знает про COM, ядро — про Qt.

---

## 🧱 Структура окна

```
┌─────────────────────────────────────────────┐
│ Inventor Tools — mass export                │
├─────────────────────────────────────────────┤
│ [Массовый экспорт]                          │
│                                             │
│ Входная папка:  [____________] [...]        │
│ Выходная папка: [____________] [...]        │
│ ☑ Экспорт в STEP                            │
│ ☑ Экспорт в PDF                             │
│ [ Запустить ]                               │
│ ┌─────────────────────────────────────────┐ │
│ │ лог…                                    │ │
│ │                                         │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

Две части:

- **`ExportTab`** — вкладка со всем содержимым;
- **`MainWindow`** — окно с `QTabWidget`, куда вкладки добавляются.

Такое разделение позволяет завтра добавить вторую вкладку (например,
«Параметры детали») — достаточно `tabs.addTab(...)`, не трогая
существующую.

---

## 📦 API

### `class ExportTab(QWidget)`

Вкладка «Массовый экспорт».

#### Атрибуты (создаются в `__init__`)

| Атрибут | Тип | Что это |
|---|---|---|
| `in_edit` | `QLineEdit` | Поле входной папки |
| `out_edit` | `QLineEdit` | Поле выходной папки |
| `chk_step` | `QCheckBox` | Флаг «Экспорт в STEP» (по умолчанию вкл.) |
| `chk_pdf` | `QCheckBox` | Флаг «Экспорт в PDF» (по умолчанию вкл.) |
| `btn` | `QPushButton` | Кнопка «Запустить» |
| `log_box` | `QTextEdit` | Лог (только для чтения) |
| `worker` | `ExportWorker` или `None` | Текущий фоновый поток |

#### `start(self)`

Обработчик кнопки «Запустить». Проверяет ввод, подключается к Inventor,
создаёт и запускает `ExportWorker`.

**Возвращает:** ничего.

**Что проверяет:**

- входная папка существует (`os.path.isdir`) — иначе лог и выход;
- выходная папка указана — иначе лог и выход;
- подключение к Inventor не упало — иначе лог и выход.

При успехе: блокирует кнопку, создаёт `worker`, подключает сигналы
`log` → `log_box.append`, `done` → `_on_done`, вызывает `worker.start()`.

#### `_on_done(self, ok, fail)`

Обработчик сигнала `done` от воркера. Пишет итоговую строку в лог и
разблокирует кнопку.

#### `_folder_row(self, label, attr)`

Внутренний хелпер: собирает строку «подпись + поле + кнопка `...`».
Поле сохраняется в `self.<attr>_edit` через `setattr`, чтобы потом
обращаться как `self.in_edit` / `self.out_edit`.

#### `_pick(self, edit)`

Открывает диалог выбора папки и записывает результат в `edit`.

---

### `class MainWindow(QMainWindow)`

Главное окно. Заголовок, размер, `QTabWidget` с одной вкладкой
`ExportTab`.

| Параметр | Значение |
|---|---|
| Заголовок | `Inventor Tools — mass export` |
| Размер | 720 × 620 |
| Центральный виджет | `QTabWidget` с вкладкой «Массовый экспорт» |

---

## 💡 Пример запуска

```python
# main.py
import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

---

## 📖 Разбор по строкам

### Импорты

```python
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QCheckBox, QTextEdit,
    QTabWidget, QFileDialog,
)
from inventor_core.connection import connect
from products.mass_export.worker import ExportWorker
```

`os` — для `os.path.isdir`. Виджеты — из `PySide6.QtWidgets`. Из ядра
берём только `connect` (подключение к Inventor) и `ExportWorker`
(фоновый поток). Всё остальное — UI.

### `ExportTab.__init__`

```python
layout = QVBoxLayout(self)
layout.addLayout(self._folder_row("Входная папка:", "in"))
layout.addLayout(self._folder_row("Выходная папка:", "out"))
```

Две строки «подпись + поле + кнопка». `_folder_row` создаёт их
однотипно и сохраняет поля в `self.in_edit` / `self.out_edit`.

```python
self.chk_step = QCheckBox("Экспорт в STEP")
self.chk_step.setChecked(True)
```

Флаги форматов. По умолчанию включены оба — типичный сценарий
«экспортировать всё».

```python
self.btn = QPushButton("Запустить")
self.btn.clicked.connect(self.start)
```

Кнопка запуска. Обработчик — `start`.

```python
self.log_box = QTextEdit()
self.log_box.setReadOnly(True)
```

Лог. `setReadOnly(True)` — пользователь не может его править, только
читать.

### `_folder_row`

```python
def _folder_row(self, label, attr):
    row = QHBoxLayout()
    edit = QLineEdit()
    btn = QPushButton("...")
    btn.clicked.connect(lambda: self._pick(edit))
    row.addWidget(QLabel(label))
    row.addWidget(edit)
    row.addWidget(btn)
    setattr(self, attr + "_edit", edit)
    return row
```

Собирает строку из трёх элементов. `lambda: self._pick(edit)` —
замыкание на конкретное поле, чтобы кнопка `...` открывала диалог
именно для него. `setattr(self, attr + "_edit", edit)` — сохраняет
поле как `self.in_edit` / `self.out_edit`, чтобы потом обращаться
напрямую.

### `start`

```python
in_dir = self.in_edit.text().strip()
out_dir = self.out_edit.text().strip()
if not os.path.isdir(in_dir):
    self.log_box.append("Входная папка не существует")
    return
if not out_dir:
    self.log_box.append("Укажите выходную папку")
    return
```

Валидация ввода. Проверяем **до** подключения к Inventor — нет смысла
дёргать COM, если папки не те.

```python
try:
    app = connect()
except Exception as e:
    self.log_box.append(f"Inventor не запущен: {e}")
    return
```

Подключение к Inventor. Если не удалось — лог и выход, кнопка остаётся
активной (пользователь может запустить Inventor и попробовать снова).

```python
self.btn.setEnabled(False)
self.worker = ExportWorker(
    app, in_dir, out_dir,
    self.chk_step.isChecked(), self.chk_pdf.isChecked(),
)
self.worker.log.connect(self.log_box.append)
self.worker.done.connect(self._on_done)
self.worker.start()
```

Блокируем кнопку, создаём воркер, подключаем сигналы, запускаем.
`self.worker` сохраняется в атрибуте — иначе Python соберёт объект
сборщиком мусора, и поток умрёт.

### `_on_done`

```python
def _on_done(self, ok, fail):
    self.log_box.append(f"=== Завершено: {ok} успешно, {fail} ошибок ===")
    self.btn.setEnabled(True)
```

Итоговая строка в лог + разблокировка кнопки. Теперь можно запустить
следующий экспорт (будет создан новый `ExportWorker` — см.
`export_worker.md`, раздел «Нельзя переиспользовать один воркер»).

### `MainWindow`

```python
self.setWindowTitle("Inventor Tools — mass export")
self.resize(720, 620)

tabs = QTabWidget()
tabs.addTab(ExportTab(), "Массовый экспорт")
self.setCentralWidget(tabs)
```

Заголовок, размер, вкладки. Пока одна — но структура готова к
расширению.

---

## ⚠️ Важные нюансы

### Кнопка блокируется на время экспорта

`self.btn.setEnabled(False)` в `start` и `True` в `_on_done`. Это
защищает от двух параллельных экспортов, которые подрались бы за
Inventor (он не любит одновременные вызовы из разных потоков).

### `worker` хранится в атрибуте

Если написать `ExportWorker(...).start()` без сохранения в `self`,
Python может собрать объект сборщиком мусора до завершения потока —
и экспорт оборвётся. Поэтому `self.worker = ...`.

### Ошибки — в лог, а не в диалог

Все ошибки (папка не существует, Inventor не запущен) пишутся в
`log_box`, а не в `QMessageBox`. Это осознанно: лог не блокирует UI,
и пользователь видит всю историю, а не одно последнее сообщение.

### Проверка `os.path.isdir` — только для входной папки

Выходная папка может не существовать — `run_export` создаст её через
`os.makedirs(exist_ok=True)`. Проверять её на существование не нужно,
достаточно, что она указана.

---

## 🔮 Что можно добавить дальше

- **Прогресс-бар** — воркер мог бы испускать `progress(current, total)`,
  а вкладка — обновлять `QProgressBar`. Сейчас видно только лог.
- **Кнопка «Отмена»** — аккуратное прерывание через флаг в `run_export`
  (не `QThread.terminate()` — см. `export_worker.md`).
- **Запоминание последних папок** — через `QSettings`, чтобы не выбирать
  каждый раз.
- **Вторая вкладка** — например, «Параметры детали» на основе
  `part_parameters.md`. Структура `QTabWidget` уже готова.

---

## ✅ Что даёт модуль

- **Готовый UI** для массового экспорта — папки, флаги, лог, кнопка.
- **Валидация ввода** — папки проверяются до подключения к Inventor.
- **Фоновый экспорт** — UI не зависает (`ExportWorker`).
- **Защита от двойного запуска** — кнопка блокируется.
- **Расширяемость** — `QTabWidget` позволяет добавить вкладки, не
  ломая существующую.
- **Чистое разделение** — UI отдельно, ядро отдельно.