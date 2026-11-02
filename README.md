# Inventor Tools

Инструменты для автоматизации Autodesk Inventor.

## Продукты
- **mass_export** — массовый экспорт деталей/сборок в STEP (PDF — в разработке).

## Архитектура
- `inventor_core/` — библиотека (без UI).
- `products/` — оболочки над core.

## Что уже работает
- Подключение к Inventor (`connection.py`).
- Массовый экспорт в STEP (`export.py`).
- Обход COM-коллекций (`com_helpers.py`).

## Запуск
1. Запустить Inventor.
2. `python -m products.mass_export.main` (когда будет готов UI).

## Зависимости
`pip install -r requirements.txt`