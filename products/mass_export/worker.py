"""Фоновый поток для экспорта."""
from PySide6.QtCore import QThread, Signal
from inventor_core.export import run_export


class ExportWorker(QThread):
    log = Signal(str)
    done = Signal(int, int)

    def __init__(self, app, input_dir, output_dir, do_step, do_pdf):
        super().__init__()
        self.app = app
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.do_step = do_step
        self.do_pdf = do_pdf

    def run(self):
        ok, fail = run_export(
            self.app, self.input_dir, self.output_dir,
            self.do_step, self.do_pdf,
            log=self.log.emit,
        )
        self.done.emit(ok, fail)