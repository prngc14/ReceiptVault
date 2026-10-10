from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)

from django.db.models import Q, F

from companies.models import Company

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

def create_receipt(request):

    if request.method == 'POST':

        form = ReceiptForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            receipt = form.save(
                commit=False
            )

            # Save which account created this receipt.
            if request.user.is_authenticated:
                receipt.created_by = request.user

            receipt.save()

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

def update_receipt(
    request,
    pk
):

    receipt = get_object_or_404(
        Receipt,
        pk=pk
    )

    if request.method == 'POST':

        form = ReceiptForm(
            request.POST,
            request.FILES,
            instance=receipt
        )

        if form.is_valid():

            # created_by is not in the form, so it stays
            # as the original creator.
            form.save()

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

def delete_receipt(
    request,
    pk
):

    receipt = get_object_or_404(
        Receipt,
        pk=pk
    )

    if request.method == 'POST':

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