from django.contrib import admin
from django.utils.html import format_html
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