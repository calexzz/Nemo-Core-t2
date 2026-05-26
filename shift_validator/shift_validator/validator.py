"""
Shift validation logic for work schedule management.

Functions in this module are pure (no DB access) so they
can be reused in any context: web app, CLI, tests, etc.
"""

from datetime import datetime

# ─── Константы ────────────────────────────────────────────────────────────────

MAX_SHIFT_HOURS = 12          # максимум часов в смене
MAX_CONSECUTIVE_SHIFTS = 6    # максимум смен подряд
SHIFT_HOUR_MIN = 8            # начало рабочего окна (включительно)
SHIFT_HOUR_MAX = 20           # конец рабочего окна (включительно)
MIN_ADVANCE_HOURS = 24        # минимум за сколько часов можно подать заявку


# ─── Валидация времени смены ──────────────────────────────────────────────────

def validate_shift_time(start_time: str, end_time: str) -> bool:
    """
    Проверяет корректность времени начала и конца смены.

    Правила:
    - start_time == 'Выходной' - всегда True
    - Оба времени должны быть целыми часами (минуты == 00)
    - Часы должны быть в диапазоне [SHIFT_HOUR_MIN, SHIFT_HOUR_MAX]
    - end_time должен быть строго позже start_time
    - Разница не должна превышать MAX_SHIFT_HOURS

    Args:
        start_time: Время начала в формате "HH:MM", или "Выходной"
        end_time:   Время конца в формате "HH:MM"

    Returns:
        True если время валидно, False иначе

    Examples:
        >>> validate_shift_time("09:00", "17:00")
        True
        >>> validate_shift_time("09:00", "22:00")
        False
        >>> validate_shift_time("Выходной", "")
        True
    """
    if start_time == "Выходной":
        return True

    try:
        sh, sm = int(start_time.split(":")[0]), int(start_time.split(":")[1])
        eh, em = int(end_time.split(":")[0]), int(end_time.split(":")[1])
    except (ValueError, IndexError, AttributeError):
        return False

    if sm != 0 or em != 0:
        return False

    if sh < SHIFT_HOUR_MIN or sh > SHIFT_HOUR_MAX:
        return False

    if eh < SHIFT_HOUR_MIN or eh > SHIFT_HOUR_MAX:
        return False

    if eh <= sh:
        return False

    if (eh - sh) > MAX_SHIFT_HOURS:
        return False

    return True

def get_shift_duration_hours(start_time: str, end_time: str) -> float:
    """
    Возвращает длительность смены в часах.

    Args:
        start_time: Время начала в формате "HH:MM"
        end_time:   Время конца в формате "HH:MM"

    Returns:
        Количество часов (float). 0.0 если выходной или некорректные данные.

    Examples:
        >>> get_shift_duration_hours("09:00", "17:00")
        8.0
        >>> get_shift_duration_hours("Выходной", "")
        0.0
    """
    if start_time == "Выходной":
        return 0.0

    try:
        sh = int(start_time.split(":")[0])
        sm = int(start_time.split(":")[1])
        eh = int(end_time.split(":")[0])
        em = int(end_time.split(":")[1])
        return (eh * 60 + em - sh * 60 - sm) / 60
    except (ValueError, IndexError, AttributeError):
        return 0.0

# ─── Валидация смен подряд ────────────────────────────────────────────────────

def count_max_consecutive(shift_dates: list) -> int:
    """
    Считает максимальное количество рабочих смен подряд в списке дат.

    Args:
        shift_dates: Список дат в формате "YYYY-MM-DD"
                     (могут повторяться, порядок не важен)

    Returns:
        Максимальная длина непрерывной серии смен подряд.
        Возвращает 0 для пустого списка.

    Examples:
        >>> count_max_consecutive(["2024-01-01", "2024-01-02", "2024-01-03"])
        3
        >>> count_max_consecutive(["2024-01-01", "2024-01-03"])
        1
    """
    if not shift_dates:
        return 0

    dates = sorted(set(shift_dates))
    max_consecutive = 1
    current = 1

    for i in range(1, len(dates)):
        d1 = datetime.strptime(dates[i - 1], "%Y-%m-%d")
        d2 = datetime.strptime(dates[i], "%Y-%m-%d")

        if (d2 - d1).days == 1:
            current += 1
            max_consecutive = max(max_consecutive, current)
        else:
            current = 1

    return max_consecutive


def validate_consecutive_shifts(existing_dates: list, new_date: str, max_consecutive: int = MAX_CONSECUTIVE_SHIFTS) -> bool:
    """
    Проверяет, что добавление новой смены не превысит лимит смен подряд.

    Args:
        existing_dates:  Список уже существующих дат смен ("YYYY-MM-DD")
        new_date:        Дата новой смены ("YYYY-MM-DD")
        max_consecutive: Максимально допустимое количество смен подряд
                         (по умолчанию MAX_CONSECUTIVE_SHIFTS = 6)

    Returns:
        True если добавление допустимо, False если превысит лимит

    Examples:
        >>> dates = ["2024-01-01","2024-01-02","2024-01-03",
        ...          "2024-01-04","2024-01-05","2024-01-06"]
        >>> validate_consecutive_shifts(dates, "2024-01-07")
        False
        >>> validate_consecutive_shifts(dates, "2024-01-08")
        True
    """
    all_dates = list(existing_dates) + [new_date]
    return count_max_consecutive(all_dates) <= max_consecutive

# ─── Валидация 24-часового опережения ────────────────────────────────────────

def is_within_advance_hours(shift_date: str, start_time: str, min_advance_hours: int = MIN_ADVANCE_HOURS, now: datetime = None) -> bool:
    """
    Проверяет, что заявка подана не менее чем за min_advance_hours до смены.

    Args:
        shift_date:        Дата смены ("YYYY-MM-DD")
        start_time:        Время начала смены ("HH:MM") или "Выходной"
        min_advance_hours: Минимальный запас в часах (по умолчанию 24)
        now:               Текущее время (если None — берётся datetime.now()).
                           Полезно для тестирования.

    Returns:
        True если до начала смены >= min_advance_hours, False иначе
    """
    if now is None:
        now = datetime.now()

    time_str = "00:00" if start_time == "Выходной" else start_time

    try:
        shift_dt = datetime.strptime(f"{shift_date} {time_str}", "%Y-%m-%d %H:%M")
        diff_hours = (shift_dt - now).total_seconds() / 3600
        return diff_hours >= min_advance_hours
    except (ValueError, TypeError):
        return False
