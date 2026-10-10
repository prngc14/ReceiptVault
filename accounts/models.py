from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditLog(models.Model):

    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('deactivated', 'Deactivated'),
        ('reactivated', 'Reactivated'),
        ('login', 'Logged in'),
        ('logout', 'Logged out'),
        ('failed_login', 'Failed login'),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events'
    )
    actor_username = models.CharField(max_length=150)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    record_type = models.CharField(max_length=40)
    record_label = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-created_at', '-pk')
        verbose_name = 'audit log entry'
        verbose_name_plural = 'audit log entries'

    def __str__(self):
        return f'{self.actor_username} {self.action} {self.record_label}'

    @property
    def display_title(self):
        if self.action == 'login':
            return f'{self.actor_username} logged in'
        if self.action == 'logout':
            return f'{self.actor_username} logged out'
        if self.action == 'failed_login':
            return f'Failed login attempt for {self.record_label}'
        return (
            f'{self.actor_username} {self.get_action_display().lower()} '
            f'{self.record_type} {self.record_label}'
        )

    @property
    def display_subtitle(self):
        return self.details or f'{self.record_type}: {self.record_label}'

    @property
    def icon_class(self):
        return {
            'receipt': 'receipt-bg',
            'company': 'company-bg',
            'staff account': 'staff-bg',
            'account': 'account-bg',
        }.get(self.record_type, 'account-bg')

    @property
    def icon(self):
        return {
            'receipt': '▤',
            'company': '▦',
            'staff account': '♟',
            'account': '◉',
        }.get(self.record_type, '•')

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('Audit log entries cannot be modified.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Audit log entries cannot be deleted.')
