"""
Тесты для shift_validator.

Запуск:
    pytest tests/ -v
"""

import pytest
from datetime import datetime, timedelta
from shift_validator import (
    validate_shift_time,
    get_shift_duration_hours,
    validate_consecutive_shifts,
    count_max_consecutive,
    is_within_advance_hours,
)


# ─── validate_shift_time ──────────────────────────────────────────────────────

class TestValidateShiftTime:

    def test_normal_shift(self):
        assert validate_shift_time("09:00", "17:00") is True

    def test_min_boundary(self):
        assert validate_shift_time("08:00", "09:00") is True

    def test_max_boundary(self):
        assert validate_shift_time("19:00", "20:00") is True

    def test_max_duration(self):
        # ровно 12 часов — допустимо
        assert validate_shift_time("08:00", "20:00") is True

    def test_over_max_duration(self):
        # теоретически 13 часов, но 21:00 вне окна — всё равно False
        assert validate_shift_time("08:00", "21:00") is False

    def test_start_before_window(self):
        assert validate_shift_time("07:00", "15:00") is False

    def test_end_after_window(self):
        assert validate_shift_time("09:00", "21:00") is False

    def test_end_before_start(self):
        assert validate_shift_time("17:00", "09:00") is False

    def test_same_time(self):
        assert validate_shift_time("09:00", "09:00") is False

    def test_non_zero_minutes_start(self):
        assert validate_shift_time("09:30", "17:00") is False

    def test_non_zero_minutes_end(self):
        assert validate_shift_time("09:00", "17:45") is False

    def test_vyhodnoj(self):
        assert validate_shift_time("Выходной", "") is True

    def test_vyhodnoj_with_end(self):
        assert validate_shift_time("Выходной", "17:00") is True

    def test_invalid_format(self):
        assert validate_shift_time("not-a-time", "17:00") is False

    def test_empty_strings(self):
        assert validate_shift_time("", "") is False


# ─── get_shift_duration_hours ─────────────────────────────────────────────────

class TestGetShiftDurationHours:

    def test_eight_hours(self):
        assert get_shift_duration_hours("09:00", "17:00") == 8.0

    def test_twelve_hours(self):
        assert get_shift_duration_hours("08:00", "20:00") == 12.0

    def test_one_hour(self):
        assert get_shift_duration_hours("10:00", "11:00") == 1.0

    def test_vyhodnoj(self):
        assert get_shift_duration_hours("Выходной", "") == 0.0

    def test_invalid(self):
        assert get_shift_duration_hours("bad", "data") == 0.0


# ─── count_max_consecutive ────────────────────────────────────────────────────

class TestCountMaxConsecutive:

    def test_empty(self):
        assert count_max_consecutive([]) == 0

    def test_single(self):
        assert count_max_consecutive(["2024-01-01"]) == 1

    def test_three_in_a_row(self):
        assert count_max_consecutive(["2024-01-01", "2024-01-02", "2024-01-03"]) == 3

    def test_gap_resets_counter(self):
        # 01, 02 — потом пропуск, 04, 05, 06
        assert count_max_consecutive(["2024-01-01", "2024-01-02",
                                       "2024-01-04", "2024-01-05", "2024-01-06"]) == 3

    def test_duplicates_ignored(self):
        # дубликаты не должны ломать логику
        assert count_max_consecutive(["2024-01-01", "2024-01-01", "2024-01-02"]) == 2

    def test_unsorted_input(self):
        assert count_max_consecutive(["2024-01-03", "2024-01-01", "2024-01-02"]) == 3


# ─── validate_consecutive_shifts ─────────────────────────────────────────────

class TestValidateConsecutiveShifts:

    def _six_days(self):
        return [f"2024-01-0{i}" for i in range(1, 7)]  # 01–06

    def test_seventh_day_exceeds_limit(self):
        assert validate_consecutive_shifts(self._six_days(), "2024-01-07") is False

    def test_day_with_gap_is_ok(self):
        # после разрыва можно снова
        assert validate_consecutive_shifts(self._six_days(), "2024-01-08") is True

    def test_empty_existing(self):
        assert validate_consecutive_shifts([], "2024-01-01") is True

    def test_custom_limit(self):
        dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        assert validate_consecutive_shifts(dates, "2024-01-04", max_consecutive=3) is False
        assert validate_consecutive_shifts(dates, "2024-01-04", max_consecutive=4) is True


# ─── is_within_advance_hours ──────────────────────────────────────────────────

class TestIsWithinAdvanceHours:

    def _future(self, hours=25):
        return datetime.now() + timedelta(hours=hours)

    def test_25h_in_future_ok(self):
        dt = self._future(25)
        assert is_within_advance_hours(
            dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M"), now=datetime.now()
        ) is True

    def test_23h_in_future_not_ok(self):
        dt = self._future(23)
        assert is_within_advance_hours(
            dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M"), now=datetime.now()
        ) is False

    def test_vyhodnoj_uses_midnight(self):
        # Выходной → время 00:00, если завтра 00:00 дальше чем 24ч — True
        tomorrow_midnight = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        assert is_within_advance_hours(
            tomorrow_midnight.strftime("%Y-%m-%d"), "Выходной", now=datetime.now()
        ) is True

    def test_invalid_date_returns_false(self):
        assert is_within_advance_hours("not-a-date", "09:00") is False

    def test_custom_min_hours(self):
        dt = self._future(5)
        assert is_within_advance_hours(
            dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M"),
            min_advance_hours=4, now=datetime.now()
        ) is True
        assert is_within_advance_hours(
            dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M"),
            min_advance_hours=6, now=datetime.now()
        ) is False
