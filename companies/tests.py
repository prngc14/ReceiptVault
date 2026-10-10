from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import AuditLog
from receipts.models import Receipt
from .models import Company


class CompanyDeletionTests(TestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            password='test-password',
            is_staff=True
        )
        self.staff_user = User.objects.create_user(
            username='staff',
            password='test-password'
        )

    def test_admin_can_delete_company_without_receipts_and_it_is_logged(self):
        company = Company.objects.create(company_name='Old company')
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('delete_company', args=[company.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm Delete')

        response = self.client.post(
            reverse('delete_company', args=[company.pk])
        )
        self.assertRedirects(response, reverse('company_list'))
        self.assertFalse(Company.objects.filter(pk=company.pk).exists())
        event = AuditLog.objects.get(
            action='deleted',
            record_type='company',
            record_label='Old company'
        )
        self.assertEqual(event.actor, self.admin_user)

    def test_company_with_receipts_is_preserved_and_delete_is_blocked(self):
        company = Company.objects.create(company_name='Active company')
        receipt = Receipt.objects.create(
            receipt_number='R-101',
            company=company,
            receipt_date=date(2026, 10, 10),
            total_amount=Decimal('100.00')
        )
        self.client.force_login(self.admin_user)

        list_response = self.client.get(reverse('company_list'))
        self.assertContains(list_response, 'Delete · Has receipts')
        self.assertNotContains(
            list_response,
            reverse('delete_company', args=[company.pk])
        )

        confirm_response = self.client.get(
            reverse('delete_company', args=[company.pk])
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertContains(confirm_response, '1 linked receipt(s)')
        self.assertNotContains(confirm_response, 'Confirm Delete')

        response = self.client.post(
            reverse('delete_company', args=[company.pk])
        )
        self.assertRedirects(response, reverse('company_list'))
        self.assertTrue(Company.objects.filter(pk=company.pk).exists())
        self.assertTrue(Receipt.objects.filter(pk=receipt.pk).exists())
        self.assertFalse(AuditLog.objects.filter(
            action='deleted',
            record_type='company',
            record_label='Active company'
        ).exists())

    def test_staff_cannot_delete_company(self):
        company = Company.objects.create(company_name='Protected company')
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse('delete_company', args=[company.pk])
        )

        self.assertRedirects(response, reverse('staff_dashboard'))
        self.assertTrue(Company.objects.filter(pk=company.pk).exists())

    def test_django_admin_company_delete_does_not_cascade_receipts(self):
        company = Company.objects.create(company_name='Admin protected')
        Receipt.objects.create(
            receipt_number='R-ADMIN',
            company=company,
            receipt_date=date(2026, 10, 10),
            total_amount=Decimal('100.00')
        )
        request = RequestFactory().post('/admin/companies/company/')
        request.user = self.admin_user
        company_admin = admin.site._registry[Company]

        with patch.object(company_admin, 'message_user'):
            company_admin.delete_model(request, company)

        self.assertTrue(Company.objects.filter(pk=company.pk).exists())
        self.assertTrue(Receipt.objects.filter(
            receipt_number='R-ADMIN'
        ).exists())

# Create your tests here.
