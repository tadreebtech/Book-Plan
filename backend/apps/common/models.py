from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """Класс, добавляющий модели время создания и время последнего изменения записи"""

    created_at = models.DateTimeField(db_index=True, default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
