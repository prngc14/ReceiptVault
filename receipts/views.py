from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, F
from django.urls import reverse
from django.views.decorators.http import require_GET

from companies.models import Company

from accounts.audit import describe_changes, log_activity, snapshot_instance
from .models import Receipt
from .forms import ReceiptForm


# ============================================================
# HOME
# ============================================================

def home(request):

    return render(
        request,
        'dashboard/home.html'
    )


# ============================================================
# SEARCH RECEIPTS
# ============================================================

def search_receipts(request):

    query = request.GET.get(
        'q',
        ''
    ).strip()

    companies = Company.objects.all().order_by(
        'company_name'
    )

    # NOTE: when there's no query, we intentionally do NOT list
    # every receipt (could be hundreds) — only when the user
    # actually searches for something.
    receipts = Receipt.objects.none()

    if query:

        companies = companies.filter(
            Q(company_name__icontains=query) |
            Q(address__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(contact_number__icontains=query) |
            Q(email__icontains=query)
        )

        receipts = Receipt.objects.select_related('company').filter(
            Q(receipt_number__icontains=query) |
            Q(reference_number__icontains=query) |
            Q(item_name__icontains=query) |
            Q(cashier__icontains=query) |
            Q(company__company_name__icontains=query)
        ).order_by('-receipt_date', '-id')

    return render(
        request,
        'receipts/search.html',
        {
            'query': query,
            'companies': companies,
            'receipts': receipts,
        }
    )


# ============================================================
# SEARCH SUGGESTIONS
# ============================================================

@require_GET
def search_suggestions(request):

    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse(
            {
                'companies': [],
                'receipts': [],
            }
        )

    companies = Company.objects.filter(
        company_name__icontains=query
    ).order_by(
        'company_name'
    )[:5]

    receipts = Receipt.objects.select_related(
        'company'
    ).filter(
        Q(receipt_number__icontains=query) |
        Q(reference_number__icontains=query) |
        Q(item_name__icontains=query) |
        Q(company__company_name__icontains=query)
    ).order_by(
        '-receipt_date',
        '-id'
    )[:5]

    return JsonResponse(
        {
            'companies': [
                {
                    'name': company.company_name,
                    'url': reverse(
                        'company_receipts',
                        args=[company.pk]
                    ),
                }
                for company in companies
            ],
            'receipts': [
                {
                    'name': receipt.receipt_number,
                    'detail': receipt.company.company_name,
                    'url': reverse(
                        'receipt_detail',
                        args=[receipt.pk]
                    ),
                }
                for receipt in receipts
            ],
        }
    )


# ============================================================
# COMPANY RECEIPTS
# ============================================================

def company_receipts(
    request,
    company_id
):

    company = get_object_or_404(
        Company,
        pk=company_id
    )

    receipts = Receipt.objects.filter(
        company=company
    ).select_related(
        'created_by'
    ).order_by(
        '-receipt_date',
        '-id'
    )

    return render(
        request,
        'companies/company_receipts.html',
        {
            'company': company,
            'receipts': receipts,
        }
    )


# ============================================================
# RECEIPT DETAIL
# ============================================================

def receipt_detail(
    request,
    pk
):

    receipt = get_object_or_404(
        Receipt.objects.select_related(
            'company',
            'created_by'
        ),
        pk=pk
    )

    return render(
        request,
        'receipts/receipt_detail.html',
        {
            'receipt': receipt,
        }
    )


# ============================================================
# RECEIPTS MISSING IMAGE
# ============================================================

def receipts_missing_image(request):

    receipts = Receipt.objects.filter(
        receipt_image=''
    ).select_related('company').order_by('-receipt_date')

    return render(
        request,
        'receipts/receipts_flagged.html',
        {
            'receipts': receipts,
            'page_title': 'Receipts Missing Images',
            'page_subtitle': 'These receipts have no uploaded image yet.',
        }
    )


# ============================================================
# RECEIPTS WITH OUTSTANDING BALANCE
# ============================================================

def receipts_outstanding_balance(request):

    receipts = Receipt.objects.filter(
        amount_paid__lt=F('total_amount')
    ).select_related('company').order_by('-receipt_date')

    return render(
        request,
        'receipts/receipts_flagged.html',
        {
            'receipts': receipts,
            'page_title': 'Outstanding Balances',
            'page_subtitle': 'These receipts have an unpaid balance.',
        }
    )


# ============================================================
# CREATE RECEIPT
# ============================================================

@login_required(login_url='login')
def create_receipt(request):

    if request.method == 'POST':

        form = ReceiptForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            with transaction.atomic():
                receipt = form.save(commit=False)

                # Save which account created this receipt.
                if request.user.is_authenticated:
                    receipt.created_by = request.user

                receipt.save()
                log_activity(
                    request.user,
                    'created',
                    'receipt',
                    receipt.receipt_number,
                    (
                        f'Receipt created for {receipt.company.company_name}. '
                        f'Total amount: ₱{receipt.total_amount:,.2f}; '
                        f'amount paid: ₱{receipt.amount_paid:,.2f}.'
                    )
                )

            return redirect(
                'receipt_detail',
                pk=receipt.pk
            )

    else:

        form = ReceiptForm()

    return render(
        request,
        'receipts/receipt_form.html',
        {
            'form': form,
        }
    )


# ============================================================
# UPDATE RECEIPT
# ============================================================

@login_required(login_url='login')
def update_receipt(
    request,
    pk
):

    receipt = get_object_or_404(
        Receipt,
        pk=pk
    )

    if request.method == 'POST':

        before = snapshot_instance(receipt)
        form = ReceiptForm(
            request.POST,
            request.FILES,
            instance=receipt
        )

        if form.is_valid():

            # created_by is not in the form, so it stays
            # as the original creator.
            with transaction.atomic():
                receipt = form.save()
                log_activity(
                    request.user,
                    'updated',
                    'receipt',
                    receipt.receipt_number,
                    describe_changes(
                        before,
                        snapshot_instance(receipt)
                    )
                )

            return redirect(
                'receipt_detail',
                pk=receipt.pk
            )

    else:

        form = ReceiptForm(
            instance=receipt
        )

    return render(
        request,
        'receipts/receipt_form.html',
        {
            'form': form,
            'receipt': receipt,
        }
    )


# ============================================================
# DELETE RECEIPT
# ============================================================

@login_required(login_url='login')
def delete_receipt(
    request,
    pk
):

    receipt = get_object_or_404(
        Receipt,
        pk=pk
    )

    if request.method == 'POST':

        receipt_label = receipt.receipt_number
        company_name = receipt.company.company_name
        with transaction.atomic():
            log_activity(
                request.user,
                'deleted',
                'receipt',
                receipt_label,
                f'Receipt for {company_name} deleted.'
            )
            receipt.delete()

        return redirect(
            'search_receipts'
        )

    return render(
        request,
        'receipts/receipt_delete.html',
        {
            'receipt': receipt,
        }
    )