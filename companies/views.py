from django.contrib import messages
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.audit import describe_changes, log_activity, snapshot_instance
from .models import Company
from .forms import CompanyForm


# ============================================================
# COMPANY LIST
# ============================================================

def company_list(request):

    companies = Company.objects.annotate(
        receipt_count=Count('receipts')
    ).order_by('company_name')

    return render(
        request,
        'companies/company_list.html',
        {
            'companies': companies,
        }
    )


# ============================================================
# CREATE COMPANY
# ============================================================

@login_required(login_url='login')
def create_company(request):

    if request.method == 'POST':

        form = CompanyForm(request.POST)

        if form.is_valid():

            with transaction.atomic():
                company = form.save()
                log_activity(
                    request.user,
                    'created',
                    'company',
                    company.company_name,
                    'Company record created.'
                )

            return redirect(
                'company_list'
            )

    else:

        form = CompanyForm()

    return render(
        request,
        'companies/company_form.html',
        {
            'form': form
        }
    )


# ============================================================
# DELETE COMPANY
# ADMIN ONLY; COMPANIES WITH RECEIPTS CANNOT BE DELETED
# ============================================================

@login_required(login_url='login')
def delete_company(request, pk):

    if not request.user.is_staff:
        return redirect('staff_dashboard')

    if request.method not in ('GET', 'POST'):
        return redirect('company_list')

    with transaction.atomic():
        company = get_object_or_404(
            Company.objects.select_for_update().annotate(
                receipt_count=Count('receipts')
            ),
            pk=pk
        )

        if request.method == 'POST':
            if company.receipt_count:
                messages.error(
                    request,
                    (
                        f'"{company.company_name}" cannot be deleted '
                        f'because it has {company.receipt_count} linked '
                        'receipt(s).'
                    )
                )
                return redirect('company_list')

            company_name = company.company_name
            log_activity(
                request.user,
                'deleted',
                'company',
                company_name,
                'Company record deleted.'
            )
            company.delete()
            messages.success(
                request,
                f'Company "{company_name}" was deleted.'
            )
            return redirect('company_list')

    return render(
        request,
        'companies/company_delete.html',
        {
            'company': company,
            'receipt_count': company.receipt_count,
        }
    )


# ============================================================
# EDIT COMPANY
# ============================================================

@login_required(login_url='login')
def edit_company(request, pk):

    company = get_object_or_404(
        Company,
        pk=pk
    )

    # Where to go back to after saving or cancelling
    # (the page the user came from). Only same-site URLs are allowed.
    next_url = (
        request.POST.get('next')
        or request.GET.get('next')
        or ''
    )

    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = ''

    if request.method == 'POST':

        before = snapshot_instance(company)
        form = CompanyForm(
            request.POST,
            instance=company
        )

        if form.is_valid():

            with transaction.atomic():
                company = form.save()
                log_activity(
                    request.user,
                    'updated',
                    'company',
                    company.company_name,
                    describe_changes(
                        before,
                        snapshot_instance(company)
                    )
                )

            return redirect(
                next_url or 'company_list'
            )

    else:

        form = CompanyForm(
            instance=company
        )

    return render(
        request,
        'companies/company_form.html',
        {
            'form': form,
            'company': company,
            'next': next_url,
        }
    )