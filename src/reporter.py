"""
Модуль генерации отчётов о сравнении логов сборки.

Предоставляет функции для форматирования и вывода результатов сравнения
в консоль с визуальным оформлением и цветовым выделением.
"""

from src.comparator import Summary, ComparisonResult
from src.extractor import Warning
from src.config import Config


# ANSI коды для цветного вывода
class Colors:
    """ANSI коды для цветного вывода в терминале."""

    GREEN = "\033[92m"  # Зелёный для добавленных
    RED = "\033[91m"  # Красный для удалённых
    GRAY = "\033[90m"  # Серый для неизменных
    RESET = "\033[0m"  # Сброс цвета
    BOLD = "\033[1m"  # Жирный текст


def colorize(text: str, color: str, use_colors: bool = True) -> str:
    """
    Добавляет ANSI коды для цветного вывода.

    Args:
        text: Текст для окрашивания
        color: Цвет (один из Colors.GREEN, Colors.RED, Colors.GRAY)
        use_colors: Использовать ли цвета (если False, возвращает текст без изменений)

    Returns:
        str: Текст с ANSI кодами или без них

    Examples:
        >>> colorize("test", Colors.GREEN, True)
        '\\033[92mtest\\033[0m'
        >>> colorize("test", Colors.GREEN, False)
        'test'
    """
    if not use_colors:
        return text

    return f"{color}{text}{Colors.RESET}"


def format_warning_text(
    warning: Warning, max_width: int = 80, indent: str = "  ", count: int = 1
) -> str:
    """
    Форматирует текст предупреждения с переносом длинных строк.

    Ограничивает ширину вывода и сохраняет отступы при переносе.

    Args:
        warning: Объект предупреждения
        max_width: Максимальная ширина строки (по умолчанию 80)
        indent: Отступ для переносимых строк

    Returns:
        str: Отформатированный текст

    Examples:
        >>> w = Warning(text="short", original="short", type="Warning",
        ...             stage="<test>", file_path="", line_number=0)
        >>> format_warning_text(w, 80, "  ")
        '  [Warning] short'
    """
    # Формируем префикс с типом предупреждения
    prefix = f"{indent}[{warning.type}] "

    # Используем оригинальный текст для отображения
    text = warning.original
    if count > 1:
        text += f" (x{count})"

    # Если текст короткий, возвращаем как есть
    if len(prefix + text) <= max_width:
        return prefix + text

    # Иначе переносим текст
    available_width = max_width - len(prefix)
    lines = []
    current_line = ""

    words = text.split()
    for word in words:
        if not current_line:
            current_line = word
        elif len(current_line) + 1 + len(word) <= available_width:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    # Формируем результат с отступами
    result = prefix + lines[0]
    for line in lines[1:]:
        result += "\n" + " " * len(prefix) + line

    return result


def print_summary(
    summary: Summary, old_log_path: str, new_log_path: str, use_colors: bool = True
) -> None:
    """
    Выводит общую сводку сравнения логов.

    Создаёт визуальную рамку с заголовком, показывает пути к файлам,
    общее количество Warning и Hint (было → стало), статистику по этапам.

    Args:
        summary: Объект сводки с результатами сравнения
        old_log_path: Путь к старому лог файлу
        new_log_path: Путь к новому лог файлу
        use_colors: Использовать ли цветовое выделение

    Examples:
        >>> summary = Summary(total_added=5, total_removed=2, total_unchanged=10)
        >>> print_summary(summary, "old.log", "new.log", False)
    """
    # Верхняя рамка с заголовком
    print("╔" + "═" * 62 + "╗")
    print("║" + " " * 14 + "СВОДКА СРАВНЕНИЯ СБОРОЧНЫХ ЛОГОВ" + " " * 16 + "║")
    print("╠" + "═" * 62 + "╣")
    print(f"║ Старый лог: {old_log_path:<47} ║")
    print(f"║ Новый лог:  {new_log_path:<47} ║")
    print("╚" + "═" * 62 + "╝")
    print()

    # Вычисляем общие значения
    old_warnings = (
        summary.by_type["Warning"]["removed"] + summary.by_type["Warning"]["unchanged"]
    )
    new_warnings = (
        summary.by_type["Warning"]["added"] + summary.by_type["Warning"]["unchanged"]
    )
    warnings_diff = new_warnings - old_warnings

    old_hints = (
        summary.by_type["Hint"]["removed"] + summary.by_type["Hint"]["unchanged"]
    )
    new_hints = summary.by_type["Hint"]["added"] + summary.by_type["Hint"]["unchanged"]
    hints_diff = new_hints - old_hints

    old_total = old_warnings + old_hints
    new_total = new_warnings + new_hints
    total_diff = new_total - old_total

    # Общая статистика
    print("┌─ ОБЩАЯ СТАТИСТИКА " + "─" * 40 + "┐")

    # Форматируем изменения с цветом
    warnings_change = f"({warnings_diff:+d})" if warnings_diff != 0 else ""
    if warnings_diff > 0:
        warnings_change = colorize(warnings_change, Colors.RED, use_colors)
    elif warnings_diff < 0:
        warnings_change = colorize(warnings_change, Colors.GREEN, use_colors)

    hints_change = f"({hints_diff:+d})" if hints_diff != 0 else ""
    if hints_diff > 0:
        hints_change = colorize(hints_change, Colors.RED, use_colors)
    elif hints_diff < 0:
        hints_change = colorize(hints_change, Colors.GREEN, use_colors)

    total_change = f"({total_diff:+d})" if total_diff != 0 else ""
    if total_diff > 0:
        total_change = colorize(total_change, Colors.RED, use_colors)
    elif total_diff < 0:
        total_change = colorize(total_change, Colors.GREEN, use_colors)

    print(f"│ Warnings:  {old_warnings} → {new_warnings} {warnings_change}")
    print(f"│ Hints:     {old_hints} → {new_hints} {hints_change}")
    print(f"│ Всего:     {old_total} → {new_total} {total_change}")
    print("└" + "─" * 60 + "┘")
    print()

    # Статистика по этапам (только если есть изменения)
    stages_with_changes = [r for r in summary.by_stage if r.added or r.removed]

    if stages_with_changes:
        print("┌─ ПО ЭТАПАМ СБОРКИ " + "─" * 41 + "┐")

        for result in stages_with_changes:
            # Дедуплицируем для подсчета (только уникальные)
            added_unique = {}
            for w in result.added:
                if w.text not in added_unique:
                    added_unique[w.text] = w
            
            removed_unique = {}
            for w in result.removed:
                if w.text not in removed_unique:
                    removed_unique[w.text] = w

            # Подсчитываем количество по типам для этапа (только уникальные)
            stage_removed_warnings = len([w for w in removed_unique.values() if w.type == "Warning"])
            stage_added_warnings = len([w for w in added_unique.values() if w.type == "Warning"])
            stage_unchanged_warnings = result.unchanged_warnings

            stage_removed_hints = len([w for w in removed_unique.values() if w.type == "Hint"])
            stage_added_hints = len([w for w in added_unique.values() if w.type == "Hint"])
            stage_unchanged_hints = result.unchanged_hints

            # Вычисляем старые и новые значения
            total_stage_warnings = stage_removed_warnings + stage_unchanged_warnings
            total_stage_new_warnings = stage_added_warnings + stage_unchanged_warnings

            total_stage_hints = stage_removed_hints + stage_unchanged_hints
            total_stage_new_hints = stage_added_hints + stage_unchanged_hints

            warnings_stage_diff = total_stage_new_warnings - total_stage_warnings
            hints_stage_diff = total_stage_new_hints - total_stage_hints

            print(f"│ {result.stage_name}")

            if (
                warnings_stage_diff != 0
                or total_stage_warnings > 0
                or total_stage_new_warnings > 0
            ):
                warnings_stage_change = (
                    f"({warnings_stage_diff:+d})" if warnings_stage_diff != 0 else ""
                )
                if warnings_stage_diff > 0:
                    warnings_stage_change = colorize(
                        warnings_stage_change, Colors.RED, use_colors
                    )
                elif warnings_stage_diff < 0:
                    warnings_stage_change = colorize(
                        warnings_stage_change, Colors.GREEN, use_colors
                    )
                print(
                    f"│   Warnings: {total_stage_warnings} → "
                    f"{total_stage_new_warnings} {warnings_stage_change}"
                )

            if (
                hints_stage_diff != 0
                or total_stage_hints > 0
                or total_stage_new_hints > 0
            ):
                hints_stage_change = (
                    f"({hints_stage_diff:+d})" if hints_stage_diff != 0 else ""
                )
                if hints_stage_diff > 0:
                    hints_stage_change = colorize(
                        hints_stage_change, Colors.RED, use_colors
                    )
                elif hints_stage_diff < 0:
                    hints_stage_change = colorize(
                        hints_stage_change, Colors.GREEN, use_colors
                    )
                print(
                    f"│   Hints:    {total_stage_hints} → "
                    f"{total_stage_new_hints} {hints_stage_change}"
                )

            print("│")

        print("└" + "─" * 60 + "┘")
        print()


def print_stage_details(
    result: ComparisonResult, use_colors: bool = True, show_unchanged_count: bool = True
) -> None:
    """
    Выводит детальную информацию об изменениях в конкретном этапе сборки.

    Группирует добавленные, удалённые и неизменные предупреждения.
    Показывает полный текст добавленных и удалённых, только количество неизменных.

    Args:
        result: Результат сравнения для этапа
        use_colors: Использовать ли цветовое выделение
        show_unchanged_count: Показывать ли количество неизменных предупреждений

    Examples:
        >>> result = ComparisonResult(stage_name="<test>", added=[], removed=[], unchanged_count=5)
        >>> print_stage_details(result, False, True)
    """
    print("┌─ " + result.stage_name + " " + "─" * (58 - len(result.stage_name)) + "┐")
    print("│" + " " * 60 + "│")

    # Дедуплицируем предупреждения для отображения (оставляем только уникальные по тексту)
    # Также подсчитываем количество повторений
    added_unique = {}
    added_counts = {}
    for w in result.added:
        added_counts[w.text] = added_counts.get(w.text, 0) + 1
        if w.text not in added_unique:
            added_unique[w.text] = w
    
    removed_unique = {}
    removed_counts = {}
    for w in result.removed:
        removed_counts[w.text] = removed_counts.get(w.text, 0) + 1
        if w.text not in removed_unique:
            removed_unique[w.text] = w

    # Подсчитываем количество по типам (уникальные)
    added_warnings = [w for w in added_unique.values() if w.type == "Warning"]
    added_hints = [w for w in added_unique.values() if w.type == "Hint"]
    removed_warnings = [w for w in removed_unique.values() if w.type == "Warning"]
    removed_hints = [w for w in removed_unique.values() if w.type == "Hint"]

    # Добавленные предупреждения
    if added_unique:
        header = (
            f"✚ ДОБАВЛЕНО ({len(added_warnings)} warnings, {len(added_hints)} hints):"
        )
        header = colorize(header, Colors.GREEN, use_colors)
        print(f"│ {header}")
        print("│" + " " * 60 + "│")

        for warning in added_unique.values():
            count = added_counts.get(warning.text, 1)
            formatted = format_warning_text(warning, max_width=58, indent="", count=count)
            # Разбиваем на строки если есть перенос
            lines = formatted.split("\n")
            for line in lines:
                colored_line = colorize(line, Colors.GREEN, use_colors)
                print(f"│   {colored_line}")

        print("│" + " " * 60 + "│")

    # Удалённые предупреждения
    if removed_unique:
        header = (
            f"✖ УДАЛЕНО ({len(removed_warnings)} warnings, {len(removed_hints)} hints):"
        )
        header = colorize(header, Colors.RED, use_colors)
        print(f"│ {header}")
        print("│" + " " * 60 + "│")

        for warning in removed_unique.values():
            count = removed_counts.get(warning.text, 1)
            formatted = format_warning_text(warning, max_width=58, indent="", count=count)
            # Разбиваем на строки если есть перенос
            lines = formatted.split("\n")
            for line in lines:
                colored_line = colorize(line, Colors.RED, use_colors)
                print(f"│   {colored_line}")

        print("│" + " " * 60 + "│")

    # Неизменные предупреждения (только количество)
    if show_unchanged_count and result.unchanged_count > 0:
        # Пытаемся определить количество по типам из неизменных
        # Это приблизительная оценка, так как у нас только общее количество
        unchanged_text = f"═ БЕЗ ИЗМЕНЕНИЙ: {result.unchanged_count} предупреждений"
        unchanged_text = colorize(unchanged_text, Colors.GRAY, use_colors)
        print(f"│ {unchanged_text}")

    # Если нет изменений вообще
    if not added_unique and not removed_unique:
        no_changes = "(нет изменений)"
        no_changes = colorize(no_changes, Colors.GRAY, use_colors)
        print(f"│   {no_changes}")
        print("│" + " " * 60 + "│")

    print("└" + "─" * 60 + "┘")
    print()


def generate_report(
    summary: Summary, old_log_path: str, new_log_path: str, config: Config
) -> None:
    """
    Генерирует полный отчёт о сравнении логов.

    Сначала выводит общую сводку, затем детали по каждому этапу с изменениями.
    Использует настройки из конфигурации (цвета, группировка).

    Args:
        summary: Объект сводки с результатами сравнения
        old_log_path: Путь к старому лог файлу
        new_log_path: Путь к новому лог файлу
        config: Объект конфигурации с настройками вывода

    Examples:
        >>> summary = Summary()
        >>> config = Config()
        >>> generate_report(summary, "old.log", "new.log", config)
    """
    # Получаем настройки из конфигурации
    use_colors = config.output.get("use_colors", True)
    show_unchanged_count = config.output.get("show_unchanged_count", True)
    group_by_stage = config.output.get("group_by_stage", True)

    # Выводим общую сводку
    print_summary(summary, old_log_path, new_log_path, use_colors)

    # Если есть изменения, выводим детали
    stages_with_changes = [r for r in summary.by_stage if r.added or r.removed]

    if stages_with_changes and group_by_stage:
        # Заголовок секции с деталями
        print("╔" + "═" * 62 + "╗")
        print("║" + " " * 20 + "ДЕТАЛЬНЫЕ ИЗМЕНЕНИЯ" + " " * 23 + "║")
        print("╚" + "═" * 62 + "╝")
        print()

        # Выводим детали по каждому этапу
        for result in stages_with_changes:
            print_stage_details(result, use_colors, show_unchanged_count)

    # Если изменений нет
    if not stages_with_changes:
        no_changes_msg = "Изменений в предупреждениях не обнаружено."
        if use_colors:
            no_changes_msg = colorize(no_changes_msg, Colors.GRAY, use_colors)
        print(no_changes_msg)
        print()
