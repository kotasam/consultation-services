from django.db import models
from common.models import BaseModel


class Zoom(BaseModel):
    api_key = models.CharField(max_length=100, blank=False, null=False)
    secret_key = models.CharField(max_length=100, blank=False, null=False)

    def __str__(self):
        return "{}".format(self.id)
