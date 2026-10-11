from django import forms
from django.core.validators import MinValueValidator
from django.db.models.functions import Lower
from django.forms import BaseInlineFormSet, inlineformset_factory

from companies.models import Company
from .models import Receipt, ReceiptItem


# ============================================================
# RECEIPT FORM
# ============================================================

class ReceiptForm(forms.ModelForm):

    class Meta:
        model = Receipt
        fields = [
            'company',
            'receipt_number',
            'receipt_date',
            'sold_to',
            'sold_to_address',
            'vat_treatment',
            'tax',
            'total_amount',
            'amount_paid',
        ]
        labels = {
            'company': 'Company',
            'receipt_number': 'Invoice No.',
            'receipt_date': 'Date',
            'sold_to': 'Sold to',
            'sold_to_address': 'Address',
            'vat_treatment': 'VAT treatment (optional)',
            'tax': 'VAT amount (optional)',
            'total_amount': 'Total amount / amount due',
            'amount_paid': 'Amount paid',
        }
        widgets = {
            'company': forms.Select(attrs={'class': 'rf-input'}),
            'receipt_number': forms.TextInput(attrs={
                'class': 'rf-input',
                'autocomplete': 'off',
            }),
            'receipt_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'rf-input', 'type': 'date'},
            ),
            'sold_to': forms.TextInput(attrs={
                'class': 'rf-input',
                'autocomplete': 'off',
            }),
            'sold_to_address': forms.TextInput(attrs={
                'class': 'rf-input',
                'autocomplete': 'off',
            }),
            'vat_treatment': forms.Select(attrs={
                'class': 'rf-input',
            }),
            'tax': forms.NumberInput(attrs={
                'class': 'rf-input',
                'step': '0.01',
                'min': '0',
                'inputmode': 'decimal',
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'rf-input',
                'step': 'any',
                'min': '0',
            }),
            'amount_paid': forms.NumberInput(attrs={
                'class': 'rf-input',
                'step': 'any',
                'min': '0',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['company'].queryset = Company.objects.order_by(
            Lower('company_name')
        )
        self.fields['company'].empty_label = 'Select a company'

        # Kapag blangko: total = kabuuan ng mga item,
        # amount paid = buong total (tingnan ang views.py).
        self.fields['total_amount'].required = False
        self.fields['amount_paid'].required = False
        self.fields['tax'].required = False

        for name in ('tax', 'total_amount', 'amount_paid'):
            self.fields[name].validators.append(MinValueValidator(0))

    def clean_receipt_number(self):
        return ' '.join(
            (self.cleaned_data.get('receipt_number') or '').split()
        )

    def clean(self):
        cleaned = super().clean()

        company = cleaned.get('company')
        number = cleaned.get('receipt_number')
        vat_treatment = cleaned.get('vat_treatment')
        vat_amount = cleaned.get('tax')
        total_amount = cleaned.get('total_amount')

        if (
            vat_treatment == 'inclusive'
            and vat_amount is not None
            and total_amount is not None
            and vat_amount > total_amount
        ):
            self.add_error(
                'tax',
                'VAT amount cannot be greater than the VAT-inclusive total.'
            )

        if company and number:
            duplicates = Receipt.objects.filter(
                company=company,
                receipt_number__iexact=number
            )

            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)

            if duplicates.exists():
                self.add_error(
                    'receipt_number',
                    f'Invoice No. {number} is already recorded '
                    f'for {company.company_name}.'
                )

        return cleaned


# ============================================================
# RECEIPT ITEMS (Excel-style rows)
# ============================================================

class ReceiptItemForm(forms.ModelForm):

    class Meta:
        model = ReceiptItem
        fields = [
            'quantity',
            'unit',
            'description',
            'unit_price',
            'amount',
        ]
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'rf-cell',
                'step': 'any',
                'min': '0',
                'inputmode': 'decimal',
            }),
            'unit': forms.TextInput(attrs={
                'class': 'rf-cell',
                'list': 'unitOptions',
                'autocomplete': 'off',
            }),
            'description': forms.TextInput(attrs={
                'class': 'rf-cell',
                'list': 'descOptions',
                'autocomplete': 'off',
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'rf-cell',
                'step': 'any',
                'min': '0',
                'inputmode': 'decimal',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'rf-cell rf-amount',
                'step': 'any',
                'min': '0',
                'inputmode': 'decimal',
                'tabindex': '-1',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Auto-fill sa Qty x Unit Price kapag blangko.
        self.fields['amount'].required = False

        # Default na unit sa bagong row.
        if not self.instance.pk and not self.initial.get('unit'):
            self.initial['unit'] = 'pcs'

    def clean_description(self):
        return ' '.join(
            (self.cleaned_data.get('description') or '').split()
        )

    def clean_quantity(self):
        value = self.cleaned_data.get('quantity')

        if value is not None and value <= 0:
            raise forms.ValidationError('Quantity must be more than 0.')

        return value

    def clean_unit_price(self):
        value = self.cleaned_data.get('unit_price')

        if value is not None and value < 0:
            raise forms.ValidationError('Price cannot be negative.')

        return value

    def clean_amount(self):
        value = self.cleaned_data.get('amount')

        if value is not None and value < 0:
            raise forms.ValidationError('Amount cannot be negative.')

        return value


class BaseItemFormSet(BaseInlineFormSet):

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        filled_rows = 0

        for form in self.forms:

            data = getattr(form, 'cleaned_data', None)

            if not data or data.get('DELETE'):
                continue

            if data.get('description'):
                filled_rows += 1

        if filled_rows == 0:
            raise forms.ValidationError(
                'Add at least one item to the receipt.'
            )


ItemFormSet = inlineformset_factory(
    Receipt,
    ReceiptItem,
    form=ReceiptItemForm,
    formset=BaseItemFormSet,
    extra=6,
    can_delete=True,
)

EditItemFormSet = inlineformset_factory(
    Receipt,
    ReceiptItem,
    form=ReceiptItemForm,
    formset=BaseItemFormSet,
    extra=2,
    can_delete=True,
)