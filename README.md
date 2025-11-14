# Build Log Comparator

Утилита для сравнения предупреждений компилятора между двумя сборочными логами. Показывает, какие Warning и Hint добавились, исчезли или остались без изменений.

## Быстрый старт

```bash
# Установка
pip install -r requirements.txt

# Запуск
python -m src.main <старый_лог> <новый_лог>

# С конфигурацией
python -m src.main old.log new.log --config config/custom.yaml

# Без цвета
python -m src.main old.log new.log --no-color
```

## Конфигурация

По умолчанию используется `config/default.yaml`. Основные параметры:

```yaml
target_steps:              # Этапы для анализа (используйте "*" для всех)
  - pattern: "Step 4/21: BuildOrionPRO"
    name: "BuildOrionPRO"

stage_markers:             # Маркеры вложенных этапов
  - "<build>"
  - "<dcc>"

warning_patterns:          # Паттерны предупреждений
  - pattern: "Warning:"
    type: "Warning"
  - pattern: "Hint:"
    type: "Hint"

ignore_patterns:           # Фильтрация временных меток и путей
  timestamp: "^\\[\\d{2}:\\d{2}:\\d{2}\\]"
  path_prefix: "N:\\\\BuildArea\\\\[^\\\\]+\\\\"

output:
  use_colors: true
  show_unchanged_count: true
  group_by_stage: true

comparison:
  ignore_case: false
```

## Структура

```
src/
├── main.py         # CLI интерфейс
├── config.py       # Конфигурация
├── parser.py       # Парсинг логов
├── extractor.py    # Извлечение предупреждений
├── comparator.py   # Сравнение
└── reporter.py     # Генерация отчётов
```

## Пример вывода

```
╔══════════════════════════════════════════════════════════════╗
║              СВОДКА СРАВНЕНИЯ СБОРОЧНЫХ ЛОГОВ                ║
╚══════════════════════════════════════════════════════════════╝

┌─ ОБЩАЯ СТАТИСТИКА ────────────────────────────────────────┐
│ Warnings:  140 → 144 (+4)
│ Hints:     2702 → 2716 (+14)
│ Всего:     2842 → 2860 (+18)
└────────────────────────────────────────────────────────────┘

┌─ <dcc> ─────────────────────────────────────────────────────┐
│ ✚ ДОБАВЛЕНО (6 warnings, 62 hints)
│ ✖ УДАЛЕНО (2 warnings, 48 hints)
│ ═ БЕЗ ИЗМЕНЕНИЙ: 2304 предупреждений
└────────────────────────────────────────────────────────────┘
```
