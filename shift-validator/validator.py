"""
Shift validation logic for work schedule management.

Functions in this module are pure (no DB access) so they
can be reused in any context: web app, CLI, tests, etc.
"""

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
