"""
Модуль сравнения предупреждений между логами сборки.

Предоставляет функции для сравнения предупреждений из двух логов,
группировки по этапам и агрегации статистики.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set
from src.extractor import Warning


@dataclass
class ComparisonResult:
    """
    Результат сравнения предупреждений для одного этапа сборки.

    Содержит списки добавленных, удалённых предупреждений и
    количество неизменных предупреждений.
    """

    stage_name: str  # Имя этапа сборки (например, "<Abd.dpr>")
    added: List[Warning] = field(default_factory=list)  # Добавленные предупреждения
    removed: List[Warning] = field(default_factory=list)  # Удалённые предупреждения
    unchanged_count: int = 0  # Количество неизменных предупреждений
    unchanged_warnings: int = 0  # Количество неизменных Warning
    unchanged_hints: int = 0  # Количество неизменных Hint


@dataclass
class Summary:
    """
    Общая сводка сравнения логов.

    Содержит агрегированную статистику по всем этапам и типам предупреждений.
    """

    total_added: int = 0  # Общее количество добавленных предупреждений
    total_removed: int = 0  # Общее количество удалённых предупреждений
    total_unchanged: int = 0  # Общее количество неизменных предупреждений

    # Статистика по типам: {"Warning": {"added": 5, "removed": 2, "unchanged": 10}, "Hint": {...}}
    by_type: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: {
            "Warning": {"added": 0, "removed": 0, "unchanged": 0},
            "Hint": {"added": 0, "removed": 0, "unchanged": 0},
        }
    )

    # Результаты по каждому этапу
    by_stage: List[ComparisonResult] = field(default_factory=list)


def group_by_stage(warnings: List[Warning]) -> Dict[str, List[Warning]]:
    """
    Группирует предупреждения по этапам сборки.

    Создаёт словарь, где ключи - имена этапов, а значения - списки
    предупреждений для каждого этапа.

    Args:
        warnings: Список предупреждений для группировки

    Returns:
        Dict[str, List[Warning]]: Словарь с группировкой по этапам

    Examples:
        >>> w1 = Warning(text="test1", original="test1", type="Warning",
        ...              stage="<Abd.dpr>", file_path="", line_number=0)
        >>> w2 = Warning(text="test2", original="test2", type="Hint",
        ...              stage="<Abd.dpr>", file_path="", line_number=0)
        >>> w3 = Warning(text="test3", original="test3", type="Warning",
        ...              stage="<Core.dpr>", file_path="", line_number=0)
        >>> grouped = group_by_stage([w1, w2, w3])
        >>> len(grouped["<Abd.dpr>"])
        2
        >>> len(grouped["<Core.dpr>"])
        1
    """
    grouped: Dict[str, List[Warning]] = {}

    for warning in warnings:
        stage_name = warning.stage

        if stage_name not in grouped:
            grouped[stage_name] = []

        grouped[stage_name].append(warning)

    return grouped


def match_stages(
    old_stages: Dict[str, List[Warning]], new_stages: Dict[str, List[Warning]]
) -> List[Tuple[str, str]]:
    """
    Сопоставляет этапы между двумя логами.

    Учитывает возможное изменение порядка этапов на одном уровне.
    Использует имена этапов для сопоставления.

    Args:
        old_stages: Словарь этапов из старого лога
        new_stages: Словарь этапов из нового лога

    Returns:
        List[Tuple[str, str]]: Список пар (имя_в_старом_логе, имя_в_новом_логе)

    Examples:
        >>> old = {"<Abd.dpr>": [], "<Core.dpr>": []}
        >>> new = {"<Core.dpr>": [], "<Abd.dpr>": [], "<New.dpr>": []}
        >>> matches = match_stages(old, new)
        >>> len(matches)
        3
        >>> ("<Abd.dpr>", "<Abd.dpr>") in matches
        True
    """
    matches: List[Tuple[str, str]] = []

    # Получаем все уникальные имена этапов из обоих логов
    all_stage_names = set(old_stages.keys()) | set(new_stages.keys())

    # Сопоставляем этапы по именам
    for stage_name in sorted(all_stage_names):
        # Этап присутствует в обоих логах или только в одном
        matches.append((stage_name, stage_name))

    return matches


def compare_logs(old_warnings: List[Warning], new_warnings: List[Warning]) -> Summary:
    """
    Сравнивает два набора предупреждений и возвращает сводку.

    Алгоритм:
    1. Группирует предупреждения по этапам
    2. Сопоставляет этапы между старым и новым логом
    3. Для каждой пары этапов находит добавленные, удалённые и неизменные предупреждения
    4. Агрегирует статистику по типам (Warning/Hint)

    Args:
        old_warnings: Список предупреждений из старого лога
        new_warnings: Список предупреждений из нового лога

    Returns:
        Summary: Объект со сводкой сравнения

    Examples:
        >>> w1 = Warning(text="test1", original="test1", type="Warning",
        ...              stage="<Abd.dpr>", file_path="", line_number=0)
        >>> w2 = Warning(text="test2", original="test2", type="Warning",
        ...              stage="<Abd.dpr>", file_path="", line_number=0)
        >>> summary = compare_logs([w1], [w1, w2])
        >>> summary.total_added
        1
        >>> summary.total_unchanged
        1
    """
    # Группируем предупреждения по этапам
    old_stages = group_by_stage(old_warnings)
    new_stages = group_by_stage(new_warnings)

    # Сопоставляем этапы
    stage_matches = match_stages(old_stages, new_stages)

    # Создаём объект сводки
    summary = Summary()

    # Сравниваем каждую пару этапов
    for old_stage_name, new_stage_name in stage_matches:
        # Получаем предупреждения для этапа (пустой список если этапа нет)
        old_stage_warnings = old_stages.get(old_stage_name, [])
        new_stage_warnings = new_stages.get(new_stage_name, [])

        # Создаём множества нормализованных текстов для сравнения
        old_texts: Set[str] = {w.text for w in old_stage_warnings}
        new_texts: Set[str] = {w.text for w in new_stage_warnings}

        # Находим добавленные, удалённые и неизменные
        added_texts = new_texts - old_texts
        removed_texts = old_texts - new_texts
        unchanged_texts = old_texts & new_texts

        # Создаём списки объектов Warning для добавленных и удалённых
        added_warnings = [w for w in new_stage_warnings if w.text in added_texts]
        removed_warnings = [w for w in old_stage_warnings if w.text in removed_texts]

        # Подсчитываем неизменные по типам
        unchanged_warnings_count = 0
        unchanged_hints_count = 0
        
        for warning in old_stage_warnings:
            if warning.text in unchanged_texts:
                if warning.type == "Warning":
                    unchanged_warnings_count += 1
                elif warning.type == "Hint":
                    unchanged_hints_count += 1

        # Создаём результат для этапа
        result = ComparisonResult(
            stage_name=new_stage_name,  # Используем имя из нового лога
            added=added_warnings,
            removed=removed_warnings,
            unchanged_count=len(unchanged_texts),
            unchanged_warnings=unchanged_warnings_count,
            unchanged_hints=unchanged_hints_count,
        )

        # Добавляем результат в сводку только если есть изменения или предупреждения
        if added_warnings or removed_warnings or result.unchanged_count > 0:
            summary.by_stage.append(result)

        # Обновляем общую статистику
        summary.total_added += len(added_warnings)
        summary.total_removed += len(removed_warnings)
        summary.total_unchanged += result.unchanged_count

        # Обновляем статистику по типам
        for warning in added_warnings:
            summary.by_type[warning.type]["added"] += 1

        for warning in removed_warnings:
            summary.by_type[warning.type]["removed"] += 1

        # Подсчитываем неизменные по типам
        for warning in old_stage_warnings:
            if warning.text in unchanged_texts:
                summary.by_type[warning.type]["unchanged"] += 1

    return summary
