"""
Modèles de base pour toutes les apps
"""

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Modèle abstrait qui ajoute created_at et updated_at
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        abstract = True
        ordering = ['-created_at']
