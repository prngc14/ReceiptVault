from django.urls import path

from .views import (
    login_view,
    logout_view,
    admin_dashboard,
    activity_log,
    staff_dashboard,
    register_staff,
    edit_staff,
    delete_staff,
)


urlpatterns = [

    # =====================================================
    # LOGIN
    # =====================================================

    path(
        'login/',
        login_view,
        name='login'
    ),


    # =====================================================
    # LOGOUT
    # =====================================================

    path(
        'logout/',
        logout_view,
        name='logout'
    ),


    # =====================================================
    # ADMIN DASHBOARD
    # =====================================================

    path(
        'admin-dashboard/',
        admin_dashboard,
        name='admin_dashboard'
    ),


    # =====================================================
    # ACTIVITY LOG
    # =====================================================

    path(
        'admin-dashboard/activity-log/',
        activity_log,
        name='activity_log'
    ),


    # =====================================================
    # STAFF DASHBOARD
    # =====================================================

    path(
        'staff/',
        staff_dashboard,
        name='staff_dashboard'
    ),


    # =====================================================
    # REGISTER STAFF
    # =====================================================

    path(
        'register-staff/',
        register_staff,
        name='register_staff'
    ),


    # =====================================================
    # EDIT STAFF
    # =====================================================

    path(
        'register-staff/<int:user_id>/edit/',
        edit_staff,
        name='edit_staff'
    ),


    # =====================================================
    # DELETE STAFF
    # =====================================================

    path(
        'register-staff/<int:user_id>/delete/',
        delete_staff,
        name='delete_staff'
    ),

]