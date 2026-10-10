from django.shortcuts import render
from django.db.models import Sum

from receipts.models import Receipt
from companies.models import Company


def dashboard(request):

    total_receipts = Receipt.objects.count()

    total_companies = Company.objects.count()

    total_amount = Receipt.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    return render(
        request,
        'dashboard/home.html',
        {
            'total_receipts': total_receipts,
            'total_companies': total_companies,
            'total_amount': total_amount,
        },
    )