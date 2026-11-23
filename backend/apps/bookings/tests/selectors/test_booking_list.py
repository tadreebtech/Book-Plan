from datetime import date, datetime

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Booking, Resource, ResourceKind
from apps.bookings.selectors import booking_list

pytestmark = pytest.mark.django_db


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    """Функция, возвращающая момент времени в декабре 2026 года в часовом поясе проекта"""

    return timezone.make_aware(datetime(2026, 12, day, hour, minute))


@pytest.fixture
def book() -> callable:
    """Функция, предоставляющая создание броней одного клиента на один ресурс"""

    user = User.objects.create_user(username="client")
    resource = Resource.objects.create(
        kind=ResourceKind.UNIVERSITY_ROOM, name="Аудитория 101", capacity=10
    )

    def create_booking(*, start: datetime, end: datetime) -> Booking:
        """Функция, сохраняющая бронь на указанный период"""

        return Booking.objects.create(
            resource=resource, user=user, start_at=start, end_at=end, guests=1
        )

    return create_booking


def test_booking_list_date_to_includes_the_whole_last_day(book) -> None:
    """Функция, проверяющая, что date_to включает бронь до последней минуты дня"""

    late_evening = book(start=_at(10, 23, 30), end=_at(10, 23, 59))
    book(start=_at(11, 0), end=_at(11, 1))

    assert list(booking_list(date_to=date(2026, 12, 10))) == [late_evening]


def test_booking_list_date_from_skips_booking_ending_at_midnight(book) -> None:
    """Функция, проверяющая, что бронь, закончившаяся в полночь, не попадает в следующий день"""

    book(start=_at(9, 23), end=_at(10, 0))
    first_minutes = book(start=_at(10, 0), end=_at(10, 0, 30))

    assert list(booking_list(date_from=date(2026, 12, 10))) == [first_minutes]


def test_booking_list_accepts_extreme_dates(book) -> None:
    """Функция, проверяющая, что крайние даты календаря не ломают выборку"""

    booking = book(start=_at(10, 9), end=_at(10, 10))

    assert list(booking_list(date_from=date.min, date_to=date.max)) == [booking]
