from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from .models import Company
from .forms import CompanyForm


# ============================================================
# COMPANY LIST
# ============================================================

def company_list(request):

    companies = Company.objects.all().order_by(
        'company_name'
    )

    return render(
        request,
        'companies/company_list.html',
        {
            'companies': companies
        }
    )


# ============================================================
# CREATE COMPANY
# ============================================================

def create_company(request):

    if request.method == 'POST':

        form = CompanyForm(request.POST)

        if form.is_valid():

            form.save()

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