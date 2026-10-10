from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from companies.models import Company
from .models import Receipt


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
