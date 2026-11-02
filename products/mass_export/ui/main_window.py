"""Главное окно продукта «Массовый экспорт»."""
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QCheckBox, QTextEdit,
    QTabWidget, QFileDialog, QApplication,
)

from inventor_core.connection import connect
from inventor_core.export import run_export


class ExportTab(QWidget):
    """Вкладка «Массовый экспорт»."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addLayout(self._folder_row("Входная папка:", "in"))
        layout.addLayout(self._folder_row("Выходная папка:", "out"))

        self.chk_step = QCheckBox("Экспорт в STEP")
        self.chk_step.setChecked(True)
        self.chk_pdf = QCheckBox("Экспорт в PDF")
        self.chk_pdf.setChecked(False)  # PDF пока отключён из-за проблемы с DWF
        layout.addWidget(self.chk_step)
        layout.addWidget(self.chk_pdf)

        self.btn = QPushButton("Запустить")
        self.btn.clicked.connect(self.start)
        layout.addWidget(self.btn)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

    def _folder_row(self, label, attr):
        """Строка «подпись + поле + кнопка ...»."""
        row = QHBoxLayout()
        edit = QLineEdit()
        btn = QPushButton("...")
        btn.clicked.connect(lambda: self._pick(edit))
        row.addWidget(QLabel(label))
        row.addWidget(edit)
        row.addWidget(btn)
        setattr(self, attr + "_edit", edit)
        return row

    def _pick(self, edit):
        d = QFileDialog.getExistingDirectory(self, "Выбор папки")
        if d:
            edit.setText(d)

    def start(self):
        in_dir = self.in_edit.text().strip()
        out_dir = self.out_edit.text().strip()
        if not os.path.isdir(in_dir):
            self.log_box.append("Входная папка не существует")
            return
        if not out_dir:
            self.log_box.append("Укажите выходную папку")
            return
        try:
            app = connect()
        except Exception as e:
            self.log_box.append(f"Inventor не запущен: {e}")
            return

        self.btn.setEnabled(False)
        self._run_export(app, in_dir, out_dir)

    def _run_export(self, app, in_dir, out_dir):
        """Синхронный экспорт с обработкой событий Qt, чтобы окно не зависало."""
        def log_and_process(msg):
            self.log_box.append(msg)
            QApplication.processEvents()  # Даём Qt перерисовать окно

        try:
            ok, fail = run_export(
                app, in_dir, out_dir,
                self.chk_step.isChecked(), self.chk_pdf.isChecked(),
                log=log_and_process,
            )
        except Exception as e:
            self.log_box.append(f"Критическая ошибка: {e}")
            ok, fail = 0, 0

        self.log_box.append(f"=== Завершено: {ok} успешно, {fail} ошибок ===")
        self.btn.setEnabled(True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventor Tools — mass export")
        self.resize(720, 620)

        tabs = QTabWidget()
        tabs.addTab(ExportTab(), "Массовый экспорт")
        self.setCentralWidget(tabs)