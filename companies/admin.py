from django.contrib import admin
from django.db import transaction

from accounts.audit import describe_changes, log_activity, snapshot_instance
from receipts.models import Receipt
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        'company_name',
        'contact_person',
        'contact_number',
        'created_at',
    )

    search_fields = (
        'company_name',
        'contact_person',
    )

    def save_model(self, request, obj, form, change):
        previous = None
        if change:
            previous = Company.objects.get(pk=obj.pk)
            before = snapshot_instance(previous)

        with transaction.atomic():
            super().save_model(request, obj, form, change)
            action = 'updated' if change else 'created'
            details = (
                describe_changes(before, snapshot_instance(obj))
                if change
                else 'Company record created.'
            )
            log_activity(
                request.user,
                action,
                'company',
                obj.company_name,
                details
            )

    def delete_model(self, request, obj):
        with transaction.atomic():
            self._log_related_receipts(request, obj)
            log_activity(
                request.user,
                'deleted',
                'company',
                obj.company_name,
                'Company record deleted.'
            )
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            for company in queryset.iterator():
                self._log_related_receipts(request, company)
                log_activity(
                    request.user,
                    'deleted',
                    'company',
                    company.company_name,
                    'Company record deleted.'
                )
            super().delete_queryset(request, queryset)

    @staticmethod
    def _log_related_receipts(request, company):
        receipts = Receipt.objects.filter(company=company).only(
            'receipt_number'
        )
        for receipt in receipts.iterator():
            log_activity(
                request.user,
                'deleted',
                'receipt',
                receipt.receipt_number,
                f'Receipt deleted with company {company.company_name}.'
            )