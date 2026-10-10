from django.contrib import admin
from django.db import transaction
from django.utils.html import format_html

from accounts.audit import describe_changes, log_activity, snapshot_instance
from .models import Receipt


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):

    list_display = (
        'receipt_number',
        'company',
        'receipt_date',
        'total_amount',
        'image_preview',
    )

    search_fields = (
        'receipt_number',
        'company__company_name',
    )

    readonly_fields = (
        'image_preview',
    )

    def image_preview(self, obj):
        if obj.receipt_image:
            return format_html(
                '<img src="{}" width="120" />',
                obj.receipt_image.url
            )
        return "No Image"

    image_preview.short_description = "Preview"

    def save_model(self, request, obj, form, change):
        if change:
            before = snapshot_instance(
                Receipt.objects.get(pk=obj.pk)
            )

        with transaction.atomic():
            super().save_model(request, obj, form, change)
            action = 'updated' if change else 'created'
            details = (
                describe_changes(before, snapshot_instance(obj))
                if change
                else (
                    f'Receipt created for {obj.company.company_name}. '
                    f'Total amount: ₱{obj.total_amount:,.2f}; '
                    f'amount paid: ₱{obj.amount_paid:,.2f}.'
                )
            )
            log_activity(
                request.user,
                action,
                'receipt',
                obj.receipt_number,
                details
            )

    def delete_model(self, request, obj):
        with transaction.atomic():
            log_activity(
                request.user,
                'deleted',
                'receipt',
                obj.receipt_number,
                f'Receipt for {obj.company.company_name} deleted.'
            )
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            for receipt in queryset.select_related('company').iterator():
                log_activity(
                    request.user,
                    'deleted',
                    'receipt',
                    receipt.receipt_number,
                    f'Receipt for {receipt.company.company_name} deleted.'
                )
            super().delete_queryset(request, queryset)