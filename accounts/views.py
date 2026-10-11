from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, Q, F
from django.urls import reverse
from django.views.decorators.http import require_POST


from companies.models import Company
from receipts.models import Receipt
from .audit import describe_changes, log_activity
from .models import AuditLog


# =========================================================
# LOGIN
# =========================================================

def login_view(request):

    if request.user.is_authenticated:
        return redirect('company_list')


    if request.method == 'POST':

        username = request.POST.get(
            'username',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(
                request,
                user
            )
            log_activity(
                user,
                'login',
                'account',
                user.get_username(),
                'Successful login.'
            )

            return redirect('company_list')

        log_activity(
            None,
            'failed_login',
            'account',
            username or 'Unknown user',
            'Invalid username or password.',
            actor_username=username or 'Anonymous'
        )

        messages.error(
            request,
            'Invalid username or password.'
        )


    return render(
        request,
        'accounts/login.html'
    )


# =========================================================
# LOGOUT
# =========================================================

def logout_view(request):

    if request.user.is_authenticated:
        log_activity(
            request.user,
            'logout',
            'account',
            request.user.get_username(),
            'User logged out.'
        )

    logout(request)

    return redirect('login')


# =========================================================
# HELPERS: PENDING TASKS
# =========================================================

def _get_pending_tasks():

    tasks = []


    # =====================================================
    # RECEIPTS MISSING IMAGE
    # =====================================================

    missing_image_count = Receipt.objects.filter(
        receipt_image=''
    ).count()

    if missing_image_count:

        tasks.append({
            'title': 'Verify receipts missing images',
            'subtitle': (
                f'{missing_image_count} receipt(s) '
                'without an uploaded image'
            ),
            'priority': 'high',
            'url': reverse(
                'receipts_missing_image'
            ),
        })


    # =====================================================
    # OUTSTANDING BALANCES
    # =====================================================

    outstanding_count = Receipt.objects.filter(
        amount_paid__lt=F('total_amount')
    ).count()

    if outstanding_count:

        tasks.append({
            'title': 'Follow up on outstanding balances',
            'subtitle': (
                f'{outstanding_count} receipt(s) '
                'with an unpaid balance'
            ),
            'priority': 'high',
            'url': reverse(
                'receipts_outstanding_balance'
            ),
        })


    # =====================================================
    # COMPANY INFORMATION
    # =====================================================

    missing_info_count = Company.objects.filter(
        Q(address='') |
        Q(contact_person='') |
        Q(contact_number='') |
        Q(email='')
    ).count()

    if missing_info_count:

        tasks.append({
            'title': 'Update company details',
            'subtitle': (
                f'{missing_info_count} company(ies) '
                'missing contact info'
            ),
            'priority': 'medium',
            'url': reverse(
                'company_list'
            ),
        })


    return tasks


# =========================================================
# RECENT ACTIVITY
# =========================================================

def _get_recent_activity(limit=None):
    if limit:
        return AuditLog.objects.select_related('actor')[:limit]

    return AuditLog.objects.select_related('actor').all()


# =========================================================
# ADMIN DASHBOARD
# Ang home page ay ang Companies list na.
# =========================================================

@login_required(login_url='login')
def admin_dashboard(request):

    if not request.user.is_staff:
        return redirect('staff_dashboard')

    return redirect('company_list')


# =========================================================
# ACTIVITY LOG
# =========================================================

@login_required(login_url='login')
def activity_log(request):

    if not request.user.is_staff:
        return redirect('staff_dashboard')


    page_obj = Paginator(
        _get_recent_activity(),
        50
    ).get_page(request.GET.get('page'))

    return render(
        request,
        'accounts/activity_log.html',
        {
            'activity': page_obj.object_list,
            'page_obj': page_obj,
        }
    )


@login_required(login_url='login')
@require_POST
def delete_activity_log_entry(request, log_id):

    if not request.user.is_staff:
        return redirect('staff_dashboard')

    entry = get_object_or_404(AuditLog, pk=log_id)

    with transaction.atomic():
        log_activity(
            request.user,
            'deleted',
            'activity log',
            f'Entry #{entry.pk}',
            (
                f'Removed {entry.actor_username} {entry.action} '
                f'{entry.record_type} "{entry.record_label}", originally '
                f'recorded at {entry.created_at.isoformat()}.'
            )
        )
        # The model blocks ordinary deletion; this path is admin-only and audited.
        AuditLog.objects.filter(pk=entry.pk).delete()

    page = request.POST.get('page', '')
    url = reverse('activity_log')
    if page.isdigit() and int(page) > 1:
        url = f'{url}?page={int(page)}'

    return redirect(url)


# =========================================================
# STAFF DASHBOARD
# Ang home page ay ang Companies list na.
# =========================================================

@login_required(login_url='login')
def staff_dashboard(request):

    if request.user.is_staff:
        return redirect('admin_dashboard')

    return redirect('company_list')


# =========================================================
# REGISTER STAFF
# ADMIN ONLY
# =========================================================

@login_required(login_url='login')
@transaction.atomic
def register_staff(request):

    # =====================================================
    # ONLY ADMIN
    # =====================================================

    if not request.user.is_staff:
        return redirect('staff_dashboard')


    # =====================================================
    # CREATE STAFF
    # =====================================================

    if request.method == 'POST':

        username = request.POST.get(
            'username',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        confirm_password = request.POST.get(
            'confirm_password',
            ''
        )


        # =================================================
        # VALIDATION
        # =================================================

        if not username:

            messages.error(
                request,
                'Username is required.'
            )

        elif not password:

            messages.error(
                request,
                'Password is required.'
            )

        elif password != confirm_password:

            messages.error(
                request,
                'Passwords do not match.'
            )

        elif User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                'Username already exists.'
            )

        else:

            # =============================================
            # CREATE STAFF ACCOUNT
            # =============================================

            staff_user = User.objects.create_user(
                username=username,
                password=password
            )

            staff_user.is_staff = False
            staff_user.is_superuser = False
            staff_user.is_active = True

            staff_user.save()

            log_activity(
                request.user,
                'created',
                'staff account',
                staff_user.username,
                'Staff account created.'
            )

            messages.success(
                request,
                f'Staff account "{username}" '
                'was created successfully.'
            )


            return redirect(
                'register_staff'
            )


    # =====================================================
    # GET STAFF ACCOUNTS
    # =====================================================

    staff_users = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).order_by(
        '-date_joined'
    )


    # =====================================================
    # DISPLAY PAGE
    # =====================================================

    return render(
        request,
        'accounts/register_staff.html',
        {
            'staff_users': staff_users,
        }
    )


# =========================================================
# EDIT STAFF ACCOUNT
# ADMIN ONLY
# =========================================================

@login_required(login_url='login')
def edit_staff(request, user_id):

    # =====================================================
    # ONLY ADMIN
    # =====================================================

    if not request.user.is_staff:
        return redirect('staff_dashboard')


    # =====================================================
    # GET STAFF ACCOUNT
    # =====================================================

    try:

        staff_user = User.objects.get(
            id=user_id,
            is_staff=False,
            is_superuser=False
        )

    except User.DoesNotExist:

        messages.error(
            request,
            'Staff account not found.'
        )

        return redirect(
            'register_staff'
        )


    # =====================================================
    # UPDATE STAFF
    # =====================================================

    if request.method == 'POST':

        username = request.POST.get(
            'username',
            ''
        ).strip()

        new_password = request.POST.get(
            'password',
            ''
        )

        confirm_password = request.POST.get(
            'confirm_password',
            ''
        )

        is_active = (
            request.POST.get('is_active')
            == 'on'
        )


        # =================================================
        # VALIDATION
        # =================================================

        if not username:

            messages.error(
                request,
                'Username is required.'
            )

            return redirect(
                'register_staff'
            )


        # =================================================
        # CHECK DUPLICATE USERNAME
        # =================================================

        username_exists = User.objects.filter(
            username=username
        ).exclude(
            id=staff_user.id
        ).exists()


        if username_exists:

            messages.error(
                request,
                'Username already exists.'
            )

            return redirect(
                'register_staff'
            )


        # =================================================
        # PASSWORD VALIDATION
        # =================================================

        staff_before = {
            'Username': staff_user.username,
            'Active': str(staff_user.is_active),
        }
        was_active = staff_user.is_active

        if new_password:

            if new_password != confirm_password:

                messages.error(
                    request,
                    'Passwords do not match.'
                )

                return redirect(
                    'register_staff'
                )

            staff_user.set_password(
                new_password
            )


        # =================================================
        # SAVE ACCOUNT
        # =================================================

        staff_user.username = username

        staff_user.is_active = is_active

        # Keep this account as STAFF only.
        staff_user.is_staff = False
        staff_user.is_superuser = False

        with transaction.atomic():
            staff_user.save()

            staff_after = {
                'Username': staff_user.username,
                'Active': str(staff_user.is_active),
            }
            details = describe_changes(staff_before, staff_after)
            if new_password:
                details = f'{details} Password changed.'

            action = 'updated'
            if was_active and not is_active:
                action = 'deactivated'
            elif not was_active and is_active:
                action = 'reactivated'

            log_activity(
                request.user,
                action,
                'staff account',
                staff_user.username,
                details
            )

        messages.success(
            request,
            f'Staff account "{username}" '
            'was updated successfully.'
        )


        return redirect(
            'register_staff'
        )


    return redirect(
        'register_staff'
    )


# =========================================================
# DELETE STAFF ACCOUNT
# ADMIN ONLY
# =========================================================

@login_required(login_url='login')
def delete_staff(request, user_id):

    # =====================================================
    # ONLY ADMIN
    # =====================================================

    if not request.user.is_staff:
        return redirect('staff_dashboard')


    # =====================================================
    # POST ONLY
    # =====================================================

    if request.method != 'POST':

        return redirect(
            'register_staff'
        )


    # =====================================================
    # GET STAFF ACCOUNT
    # Only regular staff can be deleted (never admins).
    # =====================================================

    try:

        staff_user = User.objects.get(
            id=user_id,
            is_staff=False,
            is_superuser=False
        )

    except User.DoesNotExist:

        messages.error(
            request,
            'Staff account not found.'
        )

        return redirect(
            'register_staff'
        )


    # =====================================================
    # PREVENT DELETING YOUR OWN ACCOUNT
    # =====================================================

    if staff_user.id == request.user.id:

        messages.error(
            request,
            'You cannot delete your own account.'
        )

        return redirect(
            'register_staff'
        )


    # =====================================================
    # DELETE
    # =====================================================

    username = staff_user.username

    with transaction.atomic():
        log_activity(
            request.user,
            'deleted',
            'staff account',
            username,
            'Staff account deleted.'
        )
        staff_user.delete()


    messages.success(
        request,
        f'Staff account "{username}" '
        'was deleted successfully.'
    )


    return redirect(
        'register_staff'
    )