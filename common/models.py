import uuid
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    organisation = models.CharField(max_length=50, blank=False, null=False)
    created_at = models.DateTimeField("Created at", auto_now_add=True)
    updated_at = models.DateTimeField("Updated at", auto_now=True)
    deleted_at = models.DateTimeField(
        "Deleted at", auto_now=False, blank=True, null=True
    )
    created_by = models.CharField(
        max_length=100, blank=False, null=False, default="NULL"
    )
    deleted_by = models.CharField(max_length=100, blank=True, null=True)
    updated_by = models.CharField(
        max_length=100, blank=False, null=False, default="NULL"
    )
    info = models.JSONField(blank=True, null=True, default=dict)

    class Meta:
        abstract = True
