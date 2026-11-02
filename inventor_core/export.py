"""Экспорт документов Inventor в STEP и PDF. Без UI.

STEP — для 3D-моделей (.ipt, .iam).
PDF  — для чертежей (.idw, .dwg).

PDF-аддин Inventor предназначен для чертежей: у них есть листы, рамки,
штампы. Деталь или сборка — это 3D-модель без «страницы», и PDF-аддин
не знает, как её компоновать. Поэтому PDF вызывается только для
чертёжных документов.

Для экспорта используется Document.SaveAs(path, SaveCopyAs=True):
Inventor сам выбирает транслятор по расширению файла. Это надёжнее,
чем вручную дёргать TranslatorAddIn.SaveCopyAs через win32com —
последний нестабилен из-за динамической диспетчеризации.
"""
import os

# Расширения по типам документов.
MODEL_EXTS = (".ipt", ".iam")      # 3D-модели -> STEP
DRAWING_EXTS = (".idw", ".dwg")    # чертежи   -> PDF


def _iter_files(input_dir, extensions):
    """Возвращает список файлов из input_dir с указанными расширениями."""
    result = []
    for fname in os.listdir(input_dir):
        ext = os.path.splitext(fname)[1].lower()
        if ext in extensions:
            result.append(fname)
    return result


def export_models_to_step(app, input_dir, output_dir, log=print):
    """Экспортирует все .ipt/.iam из input_dir в .stp.

    Parameters
    ----------
    app : Inventor.Application
    input_dir : str
    output_dir : str
        Создаётся, если не существует.
    log : callable
        Функция логирования (принимает строку).

    Returns
    -------
    tuple[int, int]
        (ok, fail) — количество успешных и неуспешных файлов.
    """
    os.makedirs(output_dir, exist_ok=True)
    files = _iter_files(input_dir, MODEL_EXTS)
    log(f"[STEP] Найдено моделей: {len(files)}")

    ok = fail = 0
    for fname in files:
        full = os.path.join(input_dir, fname)
        base = os.path.splitext(fname)[0]
        doc = None
        try:
            log(f"-> {fname}")
            doc = app.Documents.Open(full, False)
            out = os.path.join(output_dir, base + ".stp")
            # SaveAs с SaveCopyAs=True: Inventor сам выберет транслятор
            # по расширению файла.
            doc.SaveAs(out, True)
            log(f"   STEP -> {out}")
            ok += 1
        except Exception as e:
            log(f"   ОШИБКА: {e}")
            fail += 1
        finally:
            if doc is not None:
                try:
                    doc.Close(True)
                except Exception:
                    pass

    log(f"[STEP] Готово. Успешно: {ok}, с ошибками: {fail}")
    return ok, fail


def export_drawings_to_pdf(app, input_dir, output_dir, log=print):
    """Экспортирует все .idw/.dwg из input_dir в .pdf.

    Parameters
    ----------
    app : Inventor.Application
    input_dir : str
    output_dir : str
        Создаётся, если не существует.
    log : callable
        Функция логирования (принимает строку).

    Returns
    -------
    tuple[int, int]
        (ok, fail) — количество успешных и неуспешных файлов.
    """
    os.makedirs(output_dir, exist_ok=True)
    files = _iter_files(input_dir, DRAWING_EXTS)
    log(f"[PDF] Найдено чертежей: {len(files)}")

    ok = fail = 0
    for fname in files:
        full = os.path.join(input_dir, fname)
        base = os.path.splitext(fname)[0]
        doc = None
        try:
            log(f"-> {fname}")
            doc = app.Documents.Open(full, False)
            out = os.path.join(output_dir, base + ".pdf")
            doc.SaveAs(out, True)
            log(f"   PDF  -> {out}")
            ok += 1
        except Exception as e:
            log(f"   ОШИБКА: {e}")
            fail += 1
        finally:
            if doc is not None:
                try:
                    doc.Close(True)
                except Exception:
                    pass

    log(f"[PDF] Готово. Успешно: {ok}, с ошибками: {fail}")
    return ok, fail


def run_export(app, input_dir, output_dir, do_step=True, do_pdf=True, log=print):
    """Пакетный экспорт: STEP для моделей, PDF для чертежей.

    Parameters
    ----------
    app : Inventor.Application
    input_dir : str
        Папка с исходниками (.ipt, .iam, .idw, .dwg).
    output_dir : str
        Папка для результатов (создаётся, если нет).
    do_step : bool
        Экспортировать модели в STEP.
    do_pdf : bool
        Экспортировать чертежи в PDF.
    log : callable
        Функция логирования.

    Returns
    -------
    tuple[int, int]
        (ok, fail) — суммарно по обоим экспортам.
    """
    os.makedirs(output_dir, exist_ok=True)

    total_ok = total_fail = 0

    if do_step:
        ok, fail = export_models_to_step(app, input_dir, output_dir, log=log)
        total_ok += ok
        total_fail += fail

    if do_pdf:
        ok, fail = export_drawings_to_pdf(app, input_dir, output_dir, log=log)
        total_ok += ok
        total_fail += fail

    log(f"ИТОГО. Успешно: {total_ok}, с ошибками: {total_fail}")
    return total_ok, total_fail