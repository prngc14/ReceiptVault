from decimal import Decimal

from .models import AuditLog


def log_activity(
    actor,
    action,
    record_type,
    record_label,
    details='',
    actor_username=None,
):
    actor_name = actor_username
    if actor_name is None:
        actor_name = (
            actor.get_username()
            if actor and actor.is_authenticated
            else 'Anonymous'
        )

    return AuditLog.objects.create(
        actor=actor if actor and actor.is_authenticated else None,
        actor_username=str(actor_name)[:150],
        action=action,
        record_type=record_type,
        record_label=str(record_label)[:255],
        details=details,
    )


def snapshot_instance(instance):
    snapshot = {}
    for field in instance._meta.concrete_fields:
        if field.primary_key or field.name in {
            'created_at',
            'created_by',
            'password',
        }:
            continue

        value = getattr(instance, field.name)
        if field.is_relation:
            value = str(value) if value is not None else ''
        elif field.get_internal_type() == 'ImageField':
            value = value.name if value else ''
        elif isinstance(value, Decimal):
            value = f'₱{value:,.2f}'
        elif value is None:
            value = ''

        snapshot[field.verbose_name.capitalize()] = str(value)

    return snapshot


def describe_changes(before, after):
    changes = []
    for label, new_value in after.items():
        old_value = before.get(label, '')
        if old_value != new_value:
            changes.append(
                f'{label} changed from "{old_value or "—"}" '
                f'to "{new_value or "—"}"'
            )

    if not changes:
        return 'No field values changed.'

    return '; '.join(changes[:10])[:4000]
