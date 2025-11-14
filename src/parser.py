"""
Модуль парсинга структуры логов сборки.

Предоставляет функции для парсинга иерархической структуры логов
и извлечения целевых этапов сборки.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from src.config import Config


@dataclass
class BuildStep:
    """
    Представление этапа сборки.

    Этап может иметь вложенные подэтапы, образуя иерархическую структуру.
    """

    name: str  # Имя этапа (например, "<Abd.dpr>", "<build>")
    level: int  # Уровень вложенности (количество отступов)
    start_line: int  # Номер строки начала этапа
    end_line: int  # Номер строки окончания этапа
    lines: List[str] = field(default_factory=list)  # Строки содержимого этапа
    children: List["BuildStep"] = field(default_factory=list)  # Вложенные подэтапы


def calculate_indentation(line: str) -> int:
    """
    Вычисляет уровень вложенности строки по количеству пробельных символов.

    Обрабатывает как пробелы, так и табы. Один таб считается за 4 пробела.

    Args:
        line: Строка для анализа

    Returns:
        int: Уровень вложенности (количество отступов)

    Examples:
        >>> calculate_indentation("no indent")
        0
        >>> calculate_indentation("  two spaces")
        2
        >>> calculate_indentation("\t\tone tab")
        8
        >>> calculate_indentation("  \t  mixed")
        6
    """
    indent = 0
    for char in line:
        if char == " ":
            indent += 1
        elif char == "\t":
            indent += 4
        else:
            # Достигли первого непробельного символа
            break
    return indent


class ParseError(Exception):
    """Исключение для ошибок парсинга лога."""

    def __init__(self, message: str, line_number: Optional[int] = None):
        self.message = message
        self.line_number = line_number
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.line_number is not None:
            return f"Ошибка парсинга на строке {self.line_number}: {self.message}"
        return f"Ошибка парсинга: {self.message}"


def parse_log(log_path: str, config: Config) -> List[BuildStep]:
    """
    Парсит лог файл и возвращает дерево этапов сборки.

    Алгоритм:
    1. Читает лог построчно
    2. Определяет уровень вложенности по отступам после временной метки
    3. Идентифицирует начало этапов по маркерам из конфигурации
    4. Строит иерархическое дерево BuildStep

    Args:
        log_path: Путь к файлу лога
        config: Объект конфигурации с маркерами этапов

    Returns:
        List[BuildStep]: Список корневых этапов сборки

    Raises:
        FileNotFoundError: Если файл лога не найден
        ParseError: Если возникла ошибка при парсинге
    """
    # Читаем файл с обработкой кодировок
    lines = _read_log_file(log_path)

    # Стек для отслеживания текущей иерархии этапов
    # Каждый элемент: (уровень_вложенности, BuildStep)
    stack: List[tuple[int, BuildStep]] = []
    root_steps: List[BuildStep] = []

    line_number = 0

    for line_number, line in enumerate(lines, start=1):
        # Пропускаем пустые строки
        if not line.strip():
            continue

        # Проверяем, является ли строка началом этапа
        step_info = _extract_step_info(line, config)

        if step_info:
            step_name, indent = step_info

            # Создаем новый этап
            new_step = BuildStep(
                name=step_name,
                level=indent,
                start_line=line_number,
                end_line=line_number,
                lines=[line],
            )

            # Закрываем этапы с большим или равным уровнем вложенности
            while stack and stack[-1][0] >= indent:
                closed_step = stack.pop()
                closed_step[1].end_line = line_number - 1

            # Добавляем новый этап в иерархию
            if stack:
                # Добавляем как дочерний к последнему этапу в стеке
                parent_step = stack[-1][1]
                parent_step.children.append(new_step)
            else:
                # Добавляем как корневой этап
                root_steps.append(new_step)

            # Добавляем в стек
            stack.append((indent, new_step))
        else:
            # Добавляем строку к текущему этапу
            if stack:
                current_step = stack[-1][1]
                current_step.lines.append(line)
                current_step.end_line = line_number

    # Закрываем оставшиеся открытые этапы
    while stack:
        closed_step = stack.pop()
        closed_step[1].end_line = line_number

    return root_steps


def _extract_step_info(line: str, config: Config) -> Optional[tuple[str, int]]:
    """
    Извлекает информацию об этапе из строки.

    Новый этап начинается когда маркер появляется в содержимом строки с двоеточием после него.
    Например: [14:13:27] :\t [Step 4/21] <KeyBoxServer.dpr>: <build> (2s)

    Строки вида [14:13:28] :\t\t\t [<brcc>] Borland Resource Compiler...
    не являются новыми этапами - это содержимое текущего этапа <brcc>.

    Args:
        line: Строка для проверки
        config: Объект конфигурации с маркерами

    Returns:
        Optional[tuple[str, int]]: Кортеж (имя_этапа, уровень_вложенности) или None
    """
    import re

    # Убираем временную метку в начале строки (формат [HH:MM:SS])
    clean_line = line

    if line.strip().startswith("[") and "]" in line:
        # Находим конец временной метки
        first_bracket_end = line.index("]")
        # Пропускаем флаг (например, " :", "i:", "W:")
        after_timestamp = line[first_bracket_end + 1 :]
        if ":" in after_timestamp:
            colon_pos = after_timestamp.index(":")
            clean_line = after_timestamp[colon_pos + 1 :]
        else:
            clean_line = after_timestamp

    # Вычисляем уровень вложенности по отступам (табам) после временной метки
    indent = calculate_indentation(clean_line)

    # Убираем отступы для дальнейшего анализа
    content = clean_line.lstrip()

    # Пропускаем префикс в квадратных скобках (например, "[Step 4/21]", "[<brcc>]")
    if content.startswith("[") and "]" in content:
        bracket_end = content.index("]")
        content = content[bracket_end + 1 :].lstrip()

    # Проверяем паттерны целевых этапов (например, "Step 4/21: BuildOrionPRO")
    for target_step in config.target_steps:
        if target_step.pattern in line:
            return (target_step.name, indent)

    # Проверяем наличие маркеров этапов в угловых скобках с двоеточием после них
    # Это указывает на начало нового этапа
    pattern = r"<([^>]+)>:"
    matches = re.findall(pattern, content)

    if matches:
        # Ищем первое вхождение маркера этапа или имени проекта
        for match in matches:
            marker_with_brackets = f"<{match}>"
            # Проверяем, является ли это маркером этапа или именем проекта (.dpr файлы)
            if marker_with_brackets in config.stage_markers or match.endswith(".dpr"):
                return (marker_with_brackets, indent)

    return None


def _read_log_file(log_path: str) -> List[str]:
    """
    Читает лог файл с автоопределением кодировки.

    Пытается прочитать файл в следующих кодировках:
    1. UTF-8
    2. Windows-1251 (кириллица Windows)
    3. CP866 (кириллица DOS)

    Args:
        log_path: Путь к файлу лога

    Returns:
        List[str]: Список строк файла

    Raises:
        FileNotFoundError: Если файл не найден
        EncodingError: Если не удалось прочитать файл ни в одной кодировке
    """
    import os

    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Файл лога не найден: {log_path}")

    encodings = ["utf-8", "windows-1251", "cp866"]

    for encoding in encodings:
        try:
            with open(log_path, "r", encoding=encoding) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue

    # Если ни одна кодировка не подошла
    raise EncodingError(
        f"Не удалось прочитать файл {log_path} ни в одной из поддерживаемых кодировок: "
        f"{', '.join(encodings)}"
    )


class EncodingError(Exception):
    """Исключение для ошибок кодировки файла."""

    pass


def extract_target_steps(steps: List[BuildStep], config: Config) -> List[BuildStep]:
    """
    Извлекает только целевые этапы согласно конфигурации.

    Фильтрует этапы по паттернам из конфигурации и сохраняет
    всю иерархию внутри целевых этапов.
    
    Если в конфигурации указан паттерн "*", возвращает все этапы.

    Args:
        steps: Список всех этапов сборки
        config: Объект конфигурации с целевыми этапами

    Returns:
        List[BuildStep]: Список целевых этапов с их иерархией
    """
    # Проверяем, есть ли паттерн "*" для выбора всех этапов
    for target_step in config.target_steps:
        if target_step.pattern == "*":
            return steps
    
    target_steps = []

    for step in steps:
        # Проверяем, является ли этап целевым
        is_target = False
        for target_step in config.target_steps:
            if target_step.name == step.name or target_step.pattern in step.name:
                is_target = True
                break

        if is_target:
            # Добавляем этап со всей его иерархией
            target_steps.append(step)
        else:
            # Рекурсивно проверяем дочерние этапы
            child_targets = extract_target_steps(step.children, config)
            target_steps.extend(child_targets)

    return target_steps
