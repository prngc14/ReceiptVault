from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


# ============================================================
# ROOT
# ============================================================

def root_redirect(request):
    return redirect('login')


urlpatterns = [

    # Root → Login
    path(
        '',
        root_redirect,
        name='root'
    ),

    # ========================================================
    # ACCOUNTS
    # ========================================================

    path(
        '',
        include('accounts.urls')
    ),

    # ========================================================
    # COMPANIES
    # ========================================================

    path(
        'companies/',
        include('companies.urls')
    ),

    # ========================================================
    # RECEIPTS
    # ========================================================

    path(
        'receipts/',
        include('receipts.urls')
    ),

    # ========================================================
    # DJANGO ADMIN
    # ========================================================

    path(
        'admin/',
        admin.site.urls
    ),

]


# ============================================================
# MEDIA
# ============================================================

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )