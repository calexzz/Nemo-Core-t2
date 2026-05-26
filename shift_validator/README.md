# shift_validator

Библиотека валидации рабочих смен. Вынесена из проекта Nemo-Core-t2.

Содержит чистые функции без доступа к БД.

## Установка

pip install shift_validator


## Использование

from shift_validator import (
    validate_shift_time,
    validate_consecutive_shifts,
    is_within_advance_hours,
    get_shift_duration_hours,
)

# Проверить время смены
validate_shift_time("09:00", "17:00")   # True
validate_shift_time("09:00", "22:00")   # False
validate_shift_time("Выходной", "")     # True

# Длительность смены
get_shift_duration_hours("09:00", "17:00")  # 8.0

# Проверить лимит смен подряд (макс. 6)
existing = ["2024-01-01", "2024-01-02", "2024-01-03",
            "2024-01-04", "2024-01-05", "2024-01-06"]
validate_consecutive_shifts(existing, "2024-01-07")  # False
validate_consecutive_shifts(existing, "2024-01-08")  # True

# Проверить минимальное опережение заявки (24 часа)
is_within_advance_hours("2024-06-15", "09:00")  # True/False


## Константы

| Константа | Значение | Описание |
|---|---|---|
| MAX_SHIFT_HOURS | 12 | Максимальная длительность смены |
| MAX_CONSECUTIVE_SHIFTS | 6 | Максимум смен подряд |
| SHIFT_HOUR_MIN | 8 | Начало рабочего окна |
| SHIFT_HOUR_MAX | 20 | Конец рабочего окна |
| MIN_ADVANCE_HOURS | 24 | Минимальное опережение заявки |

## Разработка

cd shift_validator
poetry install
poetry run pytest tests/ -v


## Лицензия

MIT