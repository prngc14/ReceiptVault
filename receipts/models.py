import re
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from companies.models import Company


def normalize_search(text):
    """
    Lowercase at tanggal ang espasyo at simbolo, para magtugma ang
    "120x24T", "120 X 24T" at "120-x-24t".
    """
    return re.sub(r'[\W_]+', '', (text or '').lower())


class Receipt(models.Model):

    VAT_TREATMENT_CHOICES = [
        ('inclusive', 'VAT-inclusive (VAT is included in the total)'),
        ('added', 'Add VAT (VAT is added to sales)'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('GCash', 'GCash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('Other', 'Other'),
    ]

    # =========================
    # RECEIPT INFORMATION
    # =========================

    # Invoice No. Hindi na globally unique; unique na lang sa loob
    # ng bawat company (tingnan ang Meta sa baba).
    receipt_number = models.CharField(
        max_length=100
    )

    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='receipts'
    )

    receipt_date = models.DateField()

    sold_to = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )

    sold_to_address = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )

    # =========================
    # LEGACY (hindi na ginagamit ng bagong form;
    # iniwan para hindi masira ang lumang data at pages)
    # =========================

    item_name = models.CharField(
        max_length=255,
        blank=True
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # =========================
    # PAYMENT INFORMATION
    # =========================

    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True
    )

    cashier = models.CharField(
        max_length=255,
        blank=True
    )

    # =========================
    # FINANCIAL INFORMATION
    # =========================

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    vat_treatment = models.CharField(
        max_length=20,
        choices=VAT_TREATMENT_CHOICES,
        blank=True,
        default=''
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # =========================
    # OTHER INFORMATION
    # =========================

    remarks = models.TextField(
        blank=True
    )

    receipt_image = models.ImageField(
        upload_to='receipts/',
        blank=True,
        null=True
    )

    # =========================
    # TRACKING
    # =========================

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'receipt_number'],
                name='unique_invoice_per_company'
            ),
        ]

    def __str__(self):
        return f"{self.receipt_number} - {self.company.company_name}"

    @property
    def balance(self):
        """
        Remaining balance.
        """
        return self.total_amount - self.amount_paid

    @property
    def calculated_subtotal(self):
        """
        Quantity × Unit Price (lumang single-item na field).
        """
        return self.quantity * self.unit_price

    @property
    def net_sales(self):
        """
        Sales before VAT when the recorded VAT treatment is known.
        """
        if self.vat_treatment == 'inclusive':
            return self.total_amount - (self.tax or Decimal('0.00'))
        if self.vat_treatment == 'added':
            return self.subtotal
        return None


class ReceiptItem(models.Model):
    """
    Isang line sa resibo. Maraming item ang isang resibo.
    """

    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name='items'
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    unit = models.CharField(
        max_length=20,
        blank=True,
        default=''
    )

    description = models.CharField(
        max_length=255
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Normalized na kopya ng description, para sa search.
    search_text = models.CharField(
        max_length=255,
        blank=True,
        default='',
        editable=False
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.description} (x{self.quantity})"

    def save(self, *args, **kwargs):

        if self.amount is None:
            self.amount = (
                Decimal(self.quantity) * Decimal(self.unit_price)
            ).quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            )

        self.search_text = normalize_search(self.description)

        super().save(*args, **kwargs)