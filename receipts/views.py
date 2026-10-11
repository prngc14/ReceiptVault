from decimal import Decimal

from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, F, Count, Sum
from django.urls import reverse
from django.views.decorators.http import require_GET

from companies.models import Company

from accounts.audit import describe_changes, log_activity, snapshot_instance
from .forms import ReceiptForm, ItemFormSet, EditItemFormSet
from .models import Receipt, ReceiptItem, normalize_search


ITEM_RESULT_LIMIT = 300


# ============================================================
# HELPERS
# ============================================================

def _item_terms(text):
    """
    "ms sprocket 120 x 24t" -> ['ms', 'sprocket', '120', 'x', '24t']
    Lahat ng salita ay dapat nasa description (kahit anong ayos).
    """
    terms = []

    for part in text.split():
        term = normalize_search(part)
        if term:
            terms.append(term)

    return terms


def _known_descriptions():
    """
    Mga description na nai-type na dati, para sa suggestion
    habang nagta-type (para iisa ang spelling).
    """
    return list(
        ReceiptItem.objects
        .order_by('description')
        .values_list('description', flat=True)
        .distinct()[:1500]
    )


def _save_receipt_and_items(request, form, formset):
    """
    I-save ang resibo at ang mga item nito, at ayusin ang totals.
    Blangko ang total  -> kabuuan ng mga item (dagdag VAT kung pinili).
    Blangko ang paid   -> buong total (bayad na).
    """

    with transaction.atomic():

        receipt = form.save(commit=False)

        if receipt.pk is None:
            receipt.created_by = request.user

        if receipt.total_amount is None:
            receipt.total_amount = Decimal('0')

        if receipt.amount_paid is None:
            receipt.amount_paid = Decimal('0')

        if receipt.tax is None:
            receipt.tax = Decimal('0.00')

        receipt.save()

        formset.instance = receipt
        formset.save()

        items_total = (
            receipt.items.aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )

        if form.cleaned_data.get('total_amount') is None:
            receipt.total_amount = items_total
            if receipt.vat_treatment == 'added':
                receipt.total_amount += receipt.tax

        if form.cleaned_data.get('amount_paid') is None:
            receipt.amount_paid = receipt.total_amount

        receipt.subtotal = items_total

        receipt.save(
            update_fields=[
                'total_amount',
                'amount_paid',
                'subtotal',
            ]
        )

    return receipt


# ============================================================
# HOME
# ============================================================

@login_required(login_url='login')
def home(request):

    return render(
        request,
        'dashboard/home.html'
    )


# ============================================================
# SEARCH RECEIPTS
# ============================================================

@login_required(login_url='login')
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
            Q(items__description__icontains=query) |
            Q(sold_to__icontains=query) |
            Q(cashier__icontains=query) |
            Q(company__company_name__icontains=query)
        ).distinct().order_by('-receipt_date', '-id')

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

    empty = {
        'companies': [],
        'receipts': [],
    }

    if not request.user.is_authenticated:
        return JsonResponse(empty)

    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse(empty)

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
        Q(items__description__icontains=query) |
        Q(company__company_name__icontains=query)
    ).distinct().order_by(
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
# COMPANY RECEIPTS  (+ ITEM SEARCH SA LOOB NG COMPANY)
# ============================================================

@login_required(login_url='login')
def company_receipts(
    request,
    company_id
):

    company = get_object_or_404(
        Company,
        pk=company_id
    )

    item_query = request.GET.get(
        'item',
        ''
    ).strip()

    item_rows = None
    truncated = False

    if item_query:

        terms = _item_terms(item_query)

        if terms:

            rows = ReceiptItem.objects.filter(
                receipt__company=company
            )

            for term in terms:
                rows = rows.filter(search_text__contains=term)

            rows = rows.select_related('receipt').order_by(
                '-receipt__receipt_date',
                '-receipt__id',
                'id'
            )

            item_rows = list(rows[:ITEM_RESULT_LIMIT + 1])

            if len(item_rows) > ITEM_RESULT_LIMIT:
                truncated = True
                item_rows = item_rows[:ITEM_RESULT_LIMIT]

        else:
            item_rows = []

    receipts = Receipt.objects.filter(
        company=company
    ).annotate(
        item_count=Count('items')
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
            'item_query': item_query,
            'item_rows': item_rows,
            'truncated': truncated,
            'result_limit': ITEM_RESULT_LIMIT,
        }
    )


# ============================================================
# RECEIPT DETAIL
# ============================================================

@login_required(login_url='login')
def receipt_detail(
    request,
    pk
):

    receipt = get_object_or_404(
        Receipt.objects.select_related(
            'company',
            'created_by'
        ).prefetch_related('items'),
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

@login_required(login_url='login')
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

@login_required(login_url='login')
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

        formset = ItemFormSet(
            request.POST,
            instance=form.instance,
            prefix='items'
        )

        form_ok = form.is_valid()
        formset_ok = formset.is_valid()

        if form_ok and formset_ok:

            with transaction.atomic():

                receipt = _save_receipt_and_items(
                    request,
                    form,
                    formset
                )

                log_activity(
                    request.user,
                    'created',
                    'receipt',
                    receipt.receipt_number,
                    (
                        f'Receipt created for {receipt.company.company_name}. '
                        f'Items: {receipt.items.count()}. '
                        f'Total amount: ₱{receipt.total_amount:,.2f}; '
                        f'amount paid: ₱{receipt.amount_paid:,.2f}.'
                    )
                )

            return redirect(
                'receipt_detail',
                pk=receipt.pk
            )

    else:

        # Galing sa page ng company: "+ Add Receipt" ay may ?company=ID
        form = ReceiptForm(
            initial={
                'company': request.GET.get('company'),
            }
        )

        formset = ItemFormSet(
            instance=Receipt(),
            prefix='items'
        )

    return render(
        request,
        'receipts/receipt_form.html',
        {
            'form': form,
            'formset': formset,
            'known_descriptions': _known_descriptions(),
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

        formset = EditItemFormSet(
            request.POST,
            instance=receipt,
            prefix='items'
        )

        form_ok = form.is_valid()
        formset_ok = formset.is_valid()

        if form_ok and formset_ok:

            # created_by is not in the form, so it stays
            # as the original creator.
            with transaction.atomic():

                receipt = _save_receipt_and_items(
                    request,
                    form,
                    formset
                )

                log_activity(
                    request.user,
                    'updated',
                    'receipt',
                    receipt.receipt_number,
                    (
                        f'{describe_changes(before, snapshot_instance(receipt))} '
                        f'Items now: {receipt.items.count()}.'
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

        formset = EditItemFormSet(
            instance=receipt,
            prefix='items'
        )

    return render(
        request,
        'receipts/receipt_form.html',
        {
            'form': form,
            'formset': formset,
            'receipt': receipt,
            'known_descriptions': _known_descriptions(),
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
        company_id = receipt.company_id

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
            'company_receipts',
            company_id=company_id
        )

    return render(
        request,
        'receipts/receipt_delete.html',
        {
            'receipt': receipt,
        }
    )