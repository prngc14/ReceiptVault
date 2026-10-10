from django.urls import path

from .views import (
    company_list,
    create_company,
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

]