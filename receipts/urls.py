from django.urls import path

from .views import (
    search_receipts,
    search_suggestions,
    company_receipts,
    receipt_detail,
    create_receipt,
    update_receipt,
    delete_receipt,
    receipts_missing_image,
    receipts_outstanding_balance,
)


urlpatterns = [

    path(
        'search-suggestions/',
        search_suggestions,
        name='search_suggestions'
    ),


    # ========================================================
    # COMPANY SEARCH / COMPANY LIST
    # ========================================================

    path(
        '',
        search_receipts,
        name='search_receipts'
    ),


    # ========================================================
    # COMPANY + ALL RECEIPTS
    # ========================================================

    path(
        'company/<int:company_id>/',
        company_receipts,
        name='company_receipts'
    ),


    # ========================================================
    # CREATE RECEIPT
    # ========================================================

    path(
        'add/',
        create_receipt,
        name='create_receipt'
    ),


    # ========================================================
    # RECEIPT DETAIL
    # ========================================================

    path(
        'receipt/<int:pk>/',
        receipt_detail,
        name='receipt_detail'
    ),


    # ========================================================
    # UPDATE RECEIPT
    # ========================================================

    path(
        'edit/<int:pk>/',
        update_receipt,
        name='update_receipt'
    ),


    # ========================================================
    # DELETE RECEIPT
    # ========================================================

    path(
        'delete/<int:pk>/',
        delete_receipt,
        name='delete_receipt'
    ),


    # ========================================================
    # RECEIPTS MISSING IMAGE
    # ========================================================

    path(
        'missing-image/',
        receipts_missing_image,
        name='receipts_missing_image'
    ),


    # ========================================================
    # OUTSTANDING BALANCE
    # ========================================================

    path(
        'outstanding-balance/',
        receipts_outstanding_balance,
        name='receipts_outstanding_balance'
    ),

]