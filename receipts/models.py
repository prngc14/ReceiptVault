from django.conf import settings
from django.db import models
from companies.models import Company


class Receipt(models.Model):

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

    receipt_number = models.CharField(
        max_length=100,
        unique=True
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

    # =========================
    # ITEM INFORMATION
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
        Quantity × Unit Price.
        """
        return self.quantity * self.unit_price