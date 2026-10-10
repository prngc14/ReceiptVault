from django import forms
from .models import Receipt


class ReceiptForm(forms.ModelForm):

    class Meta:
        model = Receipt

        fields = [
            'receipt_number',
            'reference_number',
            'company',
            'receipt_date',

            'item_name',
            'quantity',
            'unit_price',

            'subtotal',
            'discount',
            'tax',
            'total_amount',
            'amount_paid',

            'payment_method',
            'cashier',

            'remarks',
            'receipt_image',
        ]

        widgets = {

            'receipt_number': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter receipt number'
                }
            ),

            'reference_number': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter reference number'
                }
            ),

            'company': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),

            'receipt_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),

            'item_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter item or product'
                }
            ),

            'quantity': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '1',
                    'placeholder': 'Quantity'
                }
            ),

            'unit_price': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0.00'
                }
            ),

            'subtotal': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0.00',
                    'readonly': 'readonly'
                }
            ),

            'discount': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0.00'
                }
            ),

            'tax': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0.00'
                }
            ),

            'total_amount': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0.00',
                    'readonly': 'readonly'
                }
            ),

            'amount_paid': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0.00'
                }
            ),

            'payment_method': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),

            'cashier': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Cashier / Prepared by'
                }
            ),

            'remarks': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Additional remarks'
                }
            ),

            'receipt_image': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control'
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')

        discount = cleaned_data.get('discount')
        tax = cleaned_data.get('tax')

        # Default values
        discount = discount or 0
        tax = tax or 0


        # =========================
        # CALCULATE SUBTOTAL
        # =========================

        if quantity is not None and unit_price is not None:

            subtotal = quantity * unit_price

            cleaned_data['subtotal'] = subtotal

        else:

            subtotal = cleaned_data.get('subtotal') or 0


        # =========================
        # CALCULATE TOTAL
        # =========================

        total = subtotal - discount + tax

        # Prevent negative total
        if total < 0:
            total = 0

        cleaned_data['total_amount'] = total


        # =========================
        # VALIDATE AMOUNT PAID
        # =========================

        amount_paid = cleaned_data.get('amount_paid') or 0

        if amount_paid < 0:

            self.add_error(
                'amount_paid',
                'Amount paid cannot be negative.'
            )


        return cleaned_data