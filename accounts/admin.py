from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db import transaction

from .audit import describe_changes, log_activity, snapshot_instance
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'actor_username',
        'action',
        'record_type',
        'record_label',
    )
    list_filter = ('action', 'record_type', 'created_at')
    search_fields = ('actor_username', 'record_label', 'details')
    readonly_fields = (
        'actor',
        'actor_username',
        'action',
        'record_type',
        'record_label',
        'details',
        'created_at',
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at', '-pk')
    actions = None

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_staff

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class AuditedUserAdmin(UserAdmin):

    def save_model(self, request, obj, form, change):
        previous = User.objects.get(pk=obj.pk) if change else None
        before = snapshot_instance(previous) if previous else {}
        password_changed = bool(
            previous and previous.password != obj.password
        )

        with transaction.atomic():
            super().save_model(request, obj, form, change)
            record_type = (
                'staff account'
                if not obj.is_staff and not obj.is_superuser
                else 'account'
            )
            details = (
                describe_changes(before, snapshot_instance(obj))
                if change
                else 'Account created.'
            )
            if password_changed:
                details = f'{details} Password changed.'

            action = 'updated' if change else 'created'
            if previous and previous.is_active and not obj.is_active:
                action = 'deactivated'
            elif previous and not previous.is_active and obj.is_active:
                action = 'reactivated'

            log_activity(
                request.user,
                action,
                record_type,
                obj.username,
                details
            )

    def delete_model(self, request, obj):
        record_type = (
            'staff account'
            if not obj.is_staff and not obj.is_superuser
            else 'account'
        )
        with transaction.atomic():
            log_activity(
                request.user,
                'deleted',
                record_type,
                obj.username,
                'Account deleted.'
            )
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            for user in queryset.iterator():
                record_type = (
                    'staff account'
                    if not user.is_staff and not user.is_superuser
                    else 'account'
                )
                log_activity(
                    request.user,
                    'deleted',
                    record_type,
                    user.username,
                    'Account deleted.'
                )
            super().delete_queryset(request, queryset)


if admin.site.is_registered(User):
    admin.site.unregister(User)
admin.site.register(User, AuditedUserAdmin)
