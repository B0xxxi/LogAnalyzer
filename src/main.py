"""
Главный модуль CLI интерфейса для утилиты сравнения логов сборки.

Предоставляет точку входа приложения и оркестрацию процесса сравнения.
"""

import argparse
import sys
import os
from typing import Optional
from src import __version__
from src.config import load_config, validate_config, ConfigValidationError
from src.parser import parse_log, extract_target_steps, ParseError, EncodingError
from src.extractor import extract_warnings
from src.comparator import compare_logs
from src.reporter import generate_report


def parse_arguments() -> argparse.Namespace:
    """
    Парсит аргументы командной строки.

    Определяет позиционные аргументы для путей к логам и опциональные
    параметры для конфигурации и настроек вывода.

    Returns:
        argparse.Namespace: Объект с распарсенными аргументами

    Examples:
        >>> import sys
        >>> sys.argv = ['main.py', 'old.log', 'new.log']
        >>> args = parse_arguments()
        >>> args.old_log
        'old.log'
    """
    parser = argparse.ArgumentParser(
        prog="build-log-comparator",
        description="Утилита для сравнения предупреждений между двумя сборочными логами",
        epilog="Пример: python -m src.main old_build.log new_build.log --config config/custom.yaml",
    )

    # Позиционные аргументы для путей к логам
    parser.add_argument("old_log", type=str, help="Путь к старому лог файлу")

    parser.add_argument("new_log", type=str, help="Путь к новому лог файлу")

    # Опциональный параметр для конфигурации
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Путь к файлу конфигурации (опционально, "
            "по умолчанию используются настройки для OrionPro)"
        ),
    )

    # Параметр для отключения цветов
    parser.add_argument(
        "--no-color", action="store_true", help="Отключить цветной вывод"
    )

    # Параметр для вывода версии
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    return parser.parse_args()


def validate_inputs(old_log: str, new_log: str, config_path: Optional[str]) -> None:
    """
    Проверяет существование входных файлов.

    Проверяет существование файлов логов и конфигурации (если указан).
    Выводит понятные сообщения об ошибках.

    Args:
        old_log: Путь к старому лог файлу
        new_log: Путь к новому лог файлу
        config_path: Путь к файлу конфигурации (опционально)

    Raises:
        FileNotFoundError: Если какой-либо из файлов не существует

    Examples:
        >>> validate_inputs('existing.log', 'existing2.log', None)
        >>> # Raises FileNotFoundError if files don't exist
    """
    # Проверяем существование старого лога
    if not os.path.exists(old_log):
        raise FileNotFoundError(f"Файл старого лога не найден: {old_log}")

    # Проверяем существование нового лога
    if not os.path.exists(new_log):
        raise FileNotFoundError(f"Файл нового лога не найден: {new_log}")

    # Проверяем существование файла конфигурации (если указан)
    if config_path is not None and not os.path.exists(config_path):
        raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")


def run_comparison(
    old_log: str, new_log: str, config_path: Optional[str], no_color: bool = False
) -> None:
    """
    Выполняет полный цикл сравнения логов.

    Оркестрирует весь процесс:
    1. Загружает конфигурацию
    2. Парсит оба лога
    3. Извлекает предупреждения
    4. Выполняет сравнение
    5. Генерирует и выводит отчёт

    Args:
        old_log: Путь к старому лог файлу
        new_log: Путь к новому лог файлу
        config_path: Путь к файлу конфигурации (опционально)
        no_color: Отключить цветной вывод

    Raises:
        FileNotFoundError: Если файл не найден
        ConfigValidationError: Если конфигурация некорректна
        ParseError: Если возникла ошибка парсинга
        EncodingError: Если не удалось прочитать файл

    Examples:
        >>> run_comparison('old.log', 'new.log', None, False)
    """
    # 1. Загружаем конфигурацию
    config = load_config(config_path)

    # Применяем параметр no_color
    if no_color:
        config.output["use_colors"] = False

    # Валидируем конфигурацию
    validate_config(config)

    # 2. Парсим старый лог
    old_steps = parse_log(old_log, config)
    old_target_steps = extract_target_steps(old_steps, config)

    # 3. Парсим новый лог
    new_steps = parse_log(new_log, config)
    new_target_steps = extract_target_steps(new_steps, config)

    # 4. Извлекаем предупреждения из старого лога
    old_warnings = []
    for step in old_target_steps:
        warnings = extract_warnings(step, config)
        old_warnings.extend(warnings)

    # 5. Извлекаем предупреждения из нового лога
    new_warnings = []
    for step in new_target_steps:
        warnings = extract_warnings(step, config)
        new_warnings.extend(warnings)

    # 6. Выполняем сравнение
    summary = compare_logs(old_warnings, new_warnings)

    # 7. Генерируем и выводим отчёт
    generate_report(summary, old_log, new_log, config)


# Коды выхода
EXIT_SUCCESS = 0  # Успешное выполнение
EXIT_FILE_NOT_FOUND = 1  # Файл не найден
EXIT_CONFIG_ERROR = 2  # Ошибка конфигурации
EXIT_PARSE_ERROR = 3  # Ошибка парсинга
EXIT_ENCODING_ERROR = 4  # Ошибка кодировки
EXIT_UNEXPECTED_ERROR = 255  # Неожиданная ошибка


def handle_error(error: Exception) -> int:
    """
    Обрабатывает ошибки и возвращает соответствующий код выхода.

    Выводит понятное сообщение об ошибке в stderr и возвращает
    код выхода в соответствии с типом ошибки.

    Args:
        error: Исключение для обработки

    Returns:
        int: Код выхода для sys.exit()

    Examples:
        >>> handle_error(FileNotFoundError("test.log"))
        1
        >>> handle_error(ConfigValidationError("Invalid config"))
        2
    """
    if isinstance(error, FileNotFoundError):
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_FILE_NOT_FOUND

    elif isinstance(error, ConfigValidationError):
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    elif isinstance(error, ParseError):
        print(f"Ошибка парсинга: {error}", file=sys.stderr)
        return EXIT_PARSE_ERROR

    elif isinstance(error, EncodingError):
        print(f"Ошибка кодировки: {error}", file=sys.stderr)
        return EXIT_ENCODING_ERROR

    else:
        # Неожиданная ошибка
        print(f"Неожиданная ошибка: {error}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        return EXIT_UNEXPECTED_ERROR


def main() -> int:
    """
    Главная функция - точка входа приложения.

    Выполняет следующие действия:
    1. Парсит аргументы командной строки
    2. Валидирует входные данные
    3. Запускает процесс сравнения
    4. Обрабатывает все исключения
    5. Возвращает корректный код выхода

    Returns:
        int: Код выхода (0 при успехе, ненулевой при ошибке)

    Examples:
        >>> # Запуск из командной строки:
        >>> # python -m src.main old.log new.log
        >>> # python -m src.main old.log new.log --config config/custom.yaml
        >>> # python -m src.main old.log new.log --no-color
    """
    try:
        # 1. Парсим аргументы командной строки
        args = parse_arguments()

        # 2. Валидируем входные данные
        validate_inputs(args.old_log, args.new_log, args.config)

        # 3. Запускаем процесс сравнения
        run_comparison(args.old_log, args.new_log, args.config, args.no_color)

        # 4. Возвращаем код успешного выполнения
        return EXIT_SUCCESS

    except Exception as error:
        # 5. Обрабатываем все исключения и возвращаем соответствующий код выхода
        return handle_error(error)


if __name__ == "__main__":
    sys.exit(main())
