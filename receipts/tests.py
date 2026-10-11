from datetime import date
from decimal import Decimal
import re

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from companies.models import Company
from .models import Receipt, ReceiptItem


class SearchSuggestionsTests(TestCase):

    def create_receipt(self, company, index):
        return Receipt.objects.create(
            receipt_number=f'RECEIPT-{index}',
            reference_number=f'REF-{index}',
            company=company,
            receipt_date=date(2025, 1, 1),
            item_name=f'Widget {index}',
            total_amount=Decimal('10.00'),
        )

    def test_queries_shorter_than_two_characters_return_no_suggestions(self):
        response = self.client.get(
            reverse('search_suggestions'),
            {'q': 'a'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'companies': [], 'receipts': []})

    def test_searches_receipt_number_reference_and_item(self):
        company = Company.objects.create(company_name='Acme Supplies')
        receipt = self.create_receipt(company, 1)

        for query in ('RECEIPT-1', 'REF-1', 'Widget'):
            with self.subTest(query=query):
                response = self.client.get(
                    reverse('search_suggestions'),
                    {'q': query}
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.json()['receipts'][0]['url'],
                    reverse('receipt_detail', args=[receipt.pk])
                )

    def test_returns_at_most_five_company_and_receipt_suggestions(self):
        for index in range(6):
            company = Company.objects.create(
                company_name=f'Acme Supplies {index}'
            )
            self.create_receipt(company, index)

        response = self.client.get(
            reverse('search_suggestions'),
            {'q': 'Acme'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['companies']), 5)
        self.assertEqual(len(response.json()['receipts']), 5)


class ReceiptFormPageTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='receipt-editor',
            password='test-password'
        )
        self.client.force_login(self.user)
        self.company = Company.objects.create(
            company_name='Acme',
            address='123 Business Road',
            contact_person='Alex Santos',
            contact_number='09171234567',
            email='alex@example.com',
        )

    def test_company_receipts_page_shows_centered_company_contacts(self):
        response = self.client.get(
            reverse('company_receipts', args=[self.company.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="cr-head"')
        self.assertContains(response, 'class="cr-heading-icon"')
        self.assertEqual(response.content.decode().count('class="cr-contact-icon"'), 4)
        self.assertContains(response, 'Acme')
        self.assertContains(response, '123 Business Road')
        self.assertContains(response, 'Contact Person:')
        self.assertContains(response, 'Alex Santos')
        self.assertContains(response, 'Contact Number / Telephone #:')
        self.assertContains(response, '09171234567')
        self.assertContains(response, 'Email Address:')
        self.assertContains(response, 'alex@example.com')
        self.assertNotContains(response, '← Companies')
        self.assertContains(response, 'class="cr-search"')
        self.assertContains(response, 'class="cr-add"')
        self.assertContains(response, 'class="cr-edit-link"')

    def test_add_receipt_form_renders_formset_and_script(self):
        response = self.client.get(reverse('create_receipt'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_items-TOTAL_FORMS"')
        self.assertContains(response, 'id="itemRows"')
        self.assertContains(response, 'id="emptyRow"')
        self.assertContains(response, 'Balance')
        self.assertContains(response, 'id="balanceValue"')
        self.assertNotContains(response, 'Photo of the receipt')
        self.assertNotContains(response, 'id_receipt_image')
        self.assertNotContains(response, 'Remarks')
        self.assertContains(response, 'data-is-edit="false"')
        self.assertNotContains(response, '{% if receipt %}')

    def test_add_receipt_prefills_company_from_company_page_link(self):
        response = self.client.get(
            reverse('create_receipt'),
            {'company': self.company.pk}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<option value="{self.company.pk}" selected>',
            html=False
        )
        companies_link = re.search(
            rf'<a\s+href="{re.escape(reverse("company_list"))}"\s+'
            r'class="sidebar-link active"',
            response.content.decode()
        )
        self.assertIsNotNone(companies_link)
        self.assertNotContains(response, 'Receipt Management')
        self.assertNotContains(response, '>Add Receipt</span>')
        self.assertNotContains(response, '>Admin</div>')

    def test_edit_receipt_form_renders_saved_items(self):
        receipt = Receipt.objects.create(
            receipt_number='R-100',
            company=self.company,
            receipt_date=date(2026, 10, 11),
            total_amount=Decimal('20.00'),
        )
        ReceiptItem.objects.create(
            receipt=receipt,
            quantity=Decimal('2'),
            unit='pcs',
            description='Widget',
            unit_price=Decimal('10.00'),
            amount=Decimal('20.00'),
        )

        response = self.client.get(
            reverse('update_receipt', args=[receipt.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_items-TOTAL_FORMS"')
        self.assertContains(response, 'value="Widget"')
        self.assertContains(response, 'data-is-edit="true"')

    def test_edit_receipt_keeps_existing_image_when_upload_is_hidden(self):
        receipt = Receipt.objects.create(
            receipt_number='R-IMAGE-PRESERVE',
            company=self.company,
            receipt_date=date(2026, 10, 11),
            total_amount=Decimal('20.00'),
            receipt_image='receipts/existing-proof.jpg',
        )
        ReceiptItem.objects.create(
            receipt=receipt,
            quantity=Decimal('2'),
            unit='pcs',
            description='Widget',
            unit_price=Decimal('10.00'),
            amount=Decimal('20.00'),
        )
        response = self.client.post(
            reverse('update_receipt', args=[receipt.pk]),
            {
                'company': self.company.pk,
                'receipt_number': 'R-IMAGE-PRESERVE',
                'receipt_date': '2026-10-11',
                'sold_to': '',
                'sold_to_address': '',
                'vat_treatment': '',
                'tax': '0',
                'total_amount': '20.00',
                'amount_paid': '20.00',
                'items-TOTAL_FORMS': '1',
                'items-INITIAL_FORMS': '1',
                'items-MIN_NUM_FORMS': '0',
                'items-MAX_NUM_FORMS': '1000',
                'items-0-id': str(receipt.items.get().pk),
                'items-0-quantity': '2',
                'items-0-unit': 'pcs',
                'items-0-description': 'Widget',
                'items-0-unit_price': '10.00',
                'items-0-amount': '20.00',
            }
        )

        self.assertEqual(response.status_code, 302)
        receipt.refresh_from_db()
        self.assertEqual(
            receipt.receipt_image.name,
            'receipts/existing-proof.jpg'
        )

    def test_add_vat_is_added_to_items_total_when_receipt_total_is_blank(self):
        response = self.client.post(
            reverse('create_receipt'),
            {
                'company': self.company.pk,
                'receipt_number': 'R-ADD-VAT',
                'receipt_date': '2026-10-11',
                'vat_treatment': 'added',
                'tax': '5.00',
                'total_amount': '',
                'amount_paid': '',
                'items-TOTAL_FORMS': '1',
                'items-INITIAL_FORMS': '0',
                'items-MIN_NUM_FORMS': '0',
                'items-MAX_NUM_FORMS': '1000',
                'items-0-quantity': '2',
                'items-0-unit': 'pcs',
                'items-0-description': 'Widgets',
                'items-0-unit_price': '20.00',
                'items-0-amount': '',
            }
        )

        self.assertEqual(response.status_code, 302)
        receipt = Receipt.objects.get(receipt_number='R-ADD-VAT')
        self.assertEqual(receipt.subtotal, Decimal('40.00'))
        self.assertEqual(receipt.tax, Decimal('5.00'))
        self.assertEqual(receipt.total_amount, Decimal('45.00'))
        self.assertEqual(receipt.amount_paid, Decimal('45.00'))

    def test_vat_inclusive_details_show_net_sales(self):
        receipt = Receipt.objects.create(
            receipt_number='R-VAT-INCLUSIVE',
            company=self.company,
            receipt_date=date(2026, 10, 11),
            total_amount=Decimal('45.00'),
            tax=Decimal('5.00'),
            vat_treatment='inclusive',
        )
        response = self.client.get(
            reverse('receipt_detail', args=[receipt.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total sales (VAT-inclusive)')
        self.assertContains(response, 'Less VAT')
        self.assertContains(response, '₱40.00')

    def test_delete_receipt_page_uses_compact_confirmation_and_deletes_on_post(self):
        receipt = Receipt.objects.create(
            receipt_number='R-DELETE',
            company=self.company,
            receipt_date=date(2026, 10, 11),
            total_amount=Decimal('20.00'),
        )
        delete_url = reverse('delete_receipt', args=[receipt.pk])

        response = self.client.get(delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="delete-page"')
        self.assertContains(response, 'R-DELETE')

        response = self.client.post(delete_url)

        self.assertRedirects(
            response,
            reverse('company_receipts', args=[self.company.pk]),
            fetch_redirect_response=False
        )
        self.assertFalse(Receipt.objects.filter(pk=receipt.pk).exists())
