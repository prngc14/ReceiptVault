from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from companies.models import Company
from receipts.models import Receipt
from .audit import describe_changes, log_activity
from .models import AuditLog


class AuditLogTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin123',
            password='test-password',
            is_staff=True,
        )

    def test_logs_failed_successful_and_logout_authentication(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'missing-user', 'password': 'wrong-password'}
        )

        self.assertEqual(response.status_code, 200)
        failed_event = AuditLog.objects.get(action='failed_login')
        self.assertEqual(failed_event.actor, None)
        self.assertEqual(failed_event.actor_username, 'missing-user')
        self.assertNotIn('wrong-password', failed_event.details)

        response = self.client.post(
            reverse('login'),
            {'username': 'admin123', 'password': 'test-password'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditLog.objects.filter(
            action='login',
            actor=self.admin
        ).exists())

        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditLog.objects.filter(
            action='logout',
            actor=self.admin
        ).exists())

    def test_company_creation_and_edit_are_logged_with_field_changes(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('create_company'),
            {
                'company_name': 'Acme',
                'address': 'Old address',
                'contact_person': 'Pat',
                'contact_number': '123',
                'email': 'pat@example.com',
            }
        )

        self.assertEqual(response.status_code, 302)
        company = Company.objects.get(company_name='Acme')
        created_event = AuditLog.objects.get(
            action='created',
            record_type='company'
        )
        self.assertEqual(created_event.actor, self.admin)

        response = self.client.post(
            reverse('edit_company', args=[company.pk]),
            {
                'company_name': 'Acme',
                'address': 'New address',
                'contact_person': 'Pat',
                'contact_number': '123',
                'email': 'pat@example.com',
            }
        )
        self.assertEqual(response.status_code, 302)
        updated_event = AuditLog.objects.get(
            action='updated',
            record_type='company'
        )
        self.assertIn('Address changed from "Old address" to "New address"',
                      updated_event.details)

    def test_activity_history_is_admin_only_and_uses_recorded_events(self):
        log_activity(
            self.admin,
            'updated',
            'receipt',
            'Receipt #002',
            'Amount changed from ₱1,500 to ₱1,800.'
        )
        company = Company.objects.create(company_name='Legacy company')
        staff_user = User.objects.create_user(
            username='staff1',
            password='test-password'
        )

        self.client.force_login(staff_user)
        response = self.client.get(reverse('activity_log'))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.admin)
        response = self.client.get(reverse('activity_log'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin123 updated receipt Receipt #002')
        self.assertContains(
            response,
            'Amount changed from ₱1,500 to ₱1,800.'
        )
        self.assertNotContains(response, 'Legacy company')
        self.assertEqual(AuditLog.objects.count(), 1)

        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin123 updated receipt Receipt #002')
        self.assertNotContains(response, 'Legacy company')

    def test_company_deletion_logs_company_and_cascaded_receipts(self):
        company = Company.objects.create(company_name='Acme')
        Receipt.objects.create(
            receipt_number='R-CASCADE',
            company=company,
            receipt_date=date(2026, 10, 10),
            total_amount=Decimal('50.00'),
        )
        request = RequestFactory().post('/admin/companies/company/')
        request.user = self.admin
        company_admin = admin.site._registry[Company]

        company_admin.delete_model(request, company)

        self.assertFalse(Company.objects.filter(pk=company.pk).exists())
        self.assertTrue(AuditLog.objects.filter(
            action='deleted',
            record_type='company',
            record_label='Acme',
            actor=self.admin,
        ).exists())
        self.assertTrue(AuditLog.objects.filter(
            action='deleted',
            record_type='receipt',
            record_label='R-CASCADE',
            actor=self.admin,
        ).exists())

    def test_audit_entries_cannot_be_edited_or_deleted(self):
        entry = log_activity(
            self.admin,
            'created',
            'company',
            'Acme',
            'Company record created.'
        )

        entry.details = 'Tampered'
        with self.assertRaises(ValidationError):
            entry.save()

        with self.assertRaises(ValidationError):
            entry.delete()

    def test_change_details_report_old_and_new_values(self):
        details = describe_changes(
            {'Total amount': '1500.00'},
            {'Total amount': '1800.00'}
        )

        self.assertEqual(
            details,
            'Total amount changed from "1500.00" to "1800.00"'
        )

    def test_staff_create_deactivate_and_delete_are_logged(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('register_staff'),
            {
                'username': 'newstaff',
                'password': 'staff-password',
                'confirm_password': 'staff-password',
            }
        )
        self.assertEqual(response.status_code, 302)
        staff_user = User.objects.get(username='newstaff')
        self.assertTrue(AuditLog.objects.filter(
            action='created',
            record_type='staff account',
            record_label='newstaff',
            actor=self.admin,
        ).exists())

        response = self.client.post(
            reverse('edit_staff', args=[staff_user.pk]),
            {'username': 'newstaff'}
        )
        self.assertEqual(response.status_code, 302)
        staff_user.refresh_from_db()
        self.assertFalse(staff_user.is_active)
        self.assertTrue(AuditLog.objects.filter(
            action='deactivated',
            record_type='staff account',
            record_label='newstaff',
            actor=self.admin,
        ).exists())

        response = self.client.post(
            reverse('delete_staff', args=[staff_user.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=staff_user.pk).exists())
        self.assertTrue(AuditLog.objects.filter(
            action='deleted',
            record_type='staff account',
            record_label='newstaff',
            actor=self.admin,
        ).exists())

    def test_receipt_create_update_and_delete_are_logged(self):
        self.client.force_login(self.admin)
        company = Company.objects.create(company_name='Acme')
        post_data = {
            'receipt_number': 'R-002',
            'reference_number': 'REF-002',
            'company': str(company.pk),
            'receipt_date': '2026-10-10',
            'item_name': 'Paper',
            'quantity': '2',
            'unit_price': '100',
            'subtotal': '200',
            'discount': '0',
            'tax': '0',
            'total_amount': '200',
            'amount_paid': '100',
            'payment_method': 'Cash',
            'cashier': 'admin123',
            'remarks': '',
        }
        response = self.client.post(
            reverse('create_receipt'),
            post_data
        )
        self.assertEqual(response.status_code, 302)
        receipt = Receipt.objects.get(receipt_number='R-002')
        self.assertTrue(AuditLog.objects.filter(
            action='created',
            record_type='receipt',
            record_label='R-002',
            actor=self.admin,
        ).exists())

        post_data['amount_paid'] = '200'
        response = self.client.post(
            reverse('update_receipt', args=[receipt.pk]),
            post_data
        )
        self.assertEqual(response.status_code, 302)
        updated_event = AuditLog.objects.get(
            action='updated',
            record_type='receipt'
        )
        self.assertIn('Amount paid changed from "₱100.00" to "₱200.00"',
                      updated_event.details)

        response = self.client.post(
            reverse('delete_receipt', args=[receipt.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Receipt.objects.filter(pk=receipt.pk).exists())
        self.assertTrue(AuditLog.objects.filter(
            action='deleted',
            record_type='receipt',
            record_label='R-002',
            actor=self.admin,
        ).exists())
