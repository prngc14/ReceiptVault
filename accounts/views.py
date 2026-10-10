from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.db.models import Sum, Q, F
from django.urls import reverse
from itertools import chain


from companies.models import Company
from receipts.models import Receipt


# =========================================================
# LOGIN
# =========================================================

def login_view(request):

    if request.user.is_authenticated:

        if request.user.is_staff:
            return redirect('admin_dashboard')

        return redirect('staff_dashboard')


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

            if user.is_staff:
                return redirect('admin_dashboard')

            return redirect('staff_dashboard')

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

    receipt_events = [
        {
            'type': 'receipt',
            'icon_class': 'receipt-bg',
            'icon': '▤',
            'title': 'New receipt added',
            'subtitle': (
                f'{r.receipt_number} — '
                f'{r.company.company_name}'
            ),
            'timestamp': r.created_at,
        }
        for r in Receipt.objects
        .select_related('company')
        .order_by('-created_at')[:50]
    ]


    company_events = [
        {
            'type': 'company',
            'icon_class': 'company-bg',
            'icon': '🏢',
            'title': 'New company added',
            'subtitle': c.company_name,
            'timestamp': c.created_at,
        }
        for c in Company.objects
        .order_by('-created_at')[:50]
    ]


    events = sorted(
        chain(
            receipt_events,
            company_events
        ),
        key=lambda item: item['timestamp'],
        reverse=True
    )


    if limit:
        return events[:limit]


    return events


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@login_required(login_url='login')
def admin_dashboard(request):

    if not request.user.is_staff:
        return redirect('staff_dashboard')


    total_staff = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).count()


    total_companies = Company.objects.count()


    total_receipts = Receipt.objects.count()


    total_amount = (
        Receipt.objects.aggregate(
            total=Sum('total_amount')
        )['total']
        or 0
    )


    return render(
        request,
        'accounts/admin_dashboard.html',
        {
            'total_staff': total_staff,
            'total_companies': total_companies,
            'total_receipts': total_receipts,
            'total_amount': total_amount,
            'pending_tasks': _get_pending_tasks(),
            'recent_activity': _get_recent_activity(
                limit=4
            ),
        }
    )


# =========================================================
# ACTIVITY LOG
# =========================================================

@login_required(login_url='login')
def activity_log(request):

    if not request.user.is_staff:
        return redirect('staff_dashboard')


    return render(
        request,
        'accounts/activity_log.html',
        {
            'activity': _get_recent_activity(),
        }
    )


# =========================================================
# STAFF DASHBOARD
# =========================================================

@login_required(login_url='login')
def staff_dashboard(request):

    if request.user.is_staff:
        return redirect('admin_dashboard')


    total_companies = Company.objects.count()


    total_receipts = Receipt.objects.count()


    total_amount = (
        Receipt.objects.aggregate(
            total=Sum('total_amount')
        )['total']
        or 0
    )


    return render(
        request,
        'accounts/staff_dashboard.html',
        {
            'total_companies': total_companies,
            'total_receipts': total_receipts,
            'total_amount': total_amount,
        }
    )


# =========================================================
# REGISTER STAFF
# ADMIN ONLY
# =========================================================

@login_required(login_url='login')
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

        staff_user.save()


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

    staff_user.delete()


    messages.success(
        request,
        f'Staff account "{username}" '
        'was deleted successfully.'
    )


    return redirect(
        'register_staff'
    )