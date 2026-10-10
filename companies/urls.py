from django.urls import path

from .views import (
    company_list,
    create_company,
    edit_company,
)

urlpatterns = [

    path(
        '',
        company_list,
        name='company_list'
    ),

    path(
        'add/',
        create_company,
        name='create_company'
    ),

    path(
        '<int:pk>/edit/',
        edit_company,
        name='edit_company'
    ),

]