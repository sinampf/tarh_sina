from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django import forms
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from datetime import datetime, timedelta
import csv
import json
import os

from .models import (
    Project, Feature, FeatureAttachment, OperatorProfile,
    ProjectPlan, TafsiliPlanData, MomayeziPlanData, MomayeziData,
    PlanRevisionHistory, FinalTafsiliData, FinalMomayeziData, UserProfile
)
# ==================== Helper Functions ====================

def is_admin(user):
    """بررسی ادمین بودن کاربر"""
    return user.is_authenticated and user.is_staff


def log_action(request, action, details=""):
    """ثبت لاگ برای عملیات‌های ادمین (نسخه موقت بدون دیتابیس)"""
    # فعلاً فقط در ترمینال چاپ کن
    print(f"[LOG] User: {request.user.username} | Action: {action} | Details: {details} | IP: {get_client_ip(request)}")
    # بعداً می‌تونی به دیتابیس اضافه کنی


def get_client_ip(request):
    """دریافت آی پی کاربر"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_setting(key, default=None):
    """دریافت تنظیمات از session (نسخه موقت)"""
    # فعلاً از session استفاده کن
    return default


def save_setting(key, value, user=None, description=""):
    """ذخیره تنظیمات در session (نسخه موقت)"""
    # فعلاً کاری نکن
    return True


# ==================== Authentication ====================

class AdminLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام کاربری'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور'})
    )


@csrf_protect
def admin_login(request):
    if request.user.is_authenticated:
        if request.user.groups.filter(name='operator').exists():
            return redirect('core_admin:operator_home')  # تغییر به operator_home
        elif request.user.groups.filter(name='expert').exists():
            return redirect('core_admin:expert_dashboard')
        elif request.user.is_staff:
            return redirect('core_admin:dashboard')
        else:
            messages.error(request, "شما دسترسی به هیچ پنلی ندارید.")
            logout(request)

    form = AdminLoginForm(request.POST or None)
    error = None
    next_url = request.GET.get('next', '')

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.groups.filter(name='operator').exists():
                return redirect('core_admin:operator_home')  # تغییر به operator_home
            elif user.groups.filter(name='expert').exists():
                return redirect('core_admin:expert_dashboard')
            elif user.is_staff:
                messages.success(request, f"خوش آمدید {user.get_full_name() or user.username}!")
                if next_url and next_url.startswith('/admin-panel/'):
                    return redirect(next_url)
                return redirect('core_admin:dashboard')
            else:
                messages.error(request, "نقش معتبری برای شما تعریف نشده است.")
                logout(request)
        else:
            error = "نام کاربری یا رمز عبور اشتباه است."

    return render(request, "core_admin/admin_login.html", {"form": form, "error": error})


def operator_login(request):
    # اگه قبلاً وارد شده و اپراتوره، ببر به پنل اپراتور
    if request.user.is_authenticated:
        if request.user.groups.filter(name='operator').exists():
            return redirect('core_admin:operator_home')  # تغییر از operator_dashboard به operator_home
        elif request.user.groups.filter(name='expert').exists():
            return redirect('core_admin:expert_dashboard')
        elif request.user.is_staff:
            return redirect('core_admin:dashboard')
        else:
            logout(request)

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is None:
            error = "نام کاربری یا رمز عبور اشتباه است."
        elif not user.groups.filter(name='operator').exists():
            error = "این کاربر اپراتور نیست. لطفاً با ادمین تماس بگیرید."
        else:
            login(request, user)
            return redirect('core_admin:operator_home')  # تغییر از operator_dashboard به operator_home

    return render(request, 'core_admin/operator_login.html', {'error': error})

# ==================== Expert Login ====================
def expert_login(request):
    if request.user.is_authenticated:
        if request.user.groups.filter(name='expert').exists():
            return redirect('core_admin:expert_dashboard')
        elif request.user.groups.filter(name='operator').exists():
            return redirect('core_admin:operator_dashboard')
        elif request.user.is_staff:
            return redirect('core_admin:dashboard')
        else:
            logout(request)

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is None:
            error = "نام کاربری یا رمز عبور اشتباه است."
        elif not user.groups.filter(name='expert').exists():
            error = "این کاربر کارشناس نیست. لطفاً با ادمین تماس بگیرید."
        else:
            login(request, user)
            return redirect('core_admin:expert_dashboard')

    return render(request, 'core_admin/expert_login.html', {'error': error})

# ==================== Expert Panel ====================
@login_required
def expert_dashboard(request):
    """پنل مخصوص کارشناسان - مشاهده و تحلیل داده‌ها"""
    if not request.user.groups.filter(name='expert').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:expert_login')
    # دریافت فیلترها
    filter_project = request.GET.get('project')
    filter_operator = request.GET.get('operator')
    filter_status = request.GET.get('status')
    filter_date_from = request.GET.get('date_from')
    filter_date_to = request.GET.get('date_to')

    # ساخت کوئری پایه برای قطعات (Features)
    features = Feature.objects.all().select_related('project', 'operator').order_by('-recorded_at')

    # اعمال فیلترها
    if filter_project:
        features = features.filter(project_id=filter_project)
    if filter_operator:
        features = features.filter(operator_id=filter_operator)
    if filter_status:
        features = features.filter(status=filter_status)
    if filter_date_from:
        features = features.filter(recorded_at__date__gte=filter_date_from)
    if filter_date_to:
        features = features.filter(recorded_at__date__lte=filter_date_to)

    # آمار قطعات
    total_features = features.count()
    pending_features = features.filter(status='submitted').count()
    approved_features = features.filter(status='approved').count()
    rejected_features = features.filter(status='rejected').count()

    # آمار طرح‌ها (از ProjectPlan)
    total_tafsili = ProjectPlan.objects.filter(plan_type='tafsili', status='approved').count()
    total_momayezi = ProjectPlan.objects.filter(plan_type='momayezi', status='approved').count()

    # صفحه‌بندی قطعات
    paginator = Paginator(features, 20)
    page = request.GET.get('page', 1)
    features_page = paginator.get_page(page)

    # لیست پروژه‌ها و اپراتورها برای فیلتر
    projects = Project.objects.filter(is_active=True)
    operators = User.objects.filter(groups__name='operator')

    # آمار عملکرد اپراتورها
    operator_stats = []
    for op in operators:
        operator_stats.append({
            'name': op.get_full_name() or op.username,
            'features_count': Feature.objects.filter(operator=op).count(),
            'tafsili_count': ProjectPlan.objects.filter(operator=op, plan_type='tafsili', status='approved').count(),
            'momayezi_count': ProjectPlan.objects.filter(operator=op, plan_type='momayezi', status='approved').count(),
            'total_count': ProjectPlan.objects.filter(operator=op, status='approved').count(),
        })

    context = {
        'user': request.user,
        'features': features_page,
        'total_features': total_features,
        'pending_features': pending_features,
        'approved_features': approved_features,
        'rejected_features': rejected_features,
        'total_tafsili': total_tafsili,
        'total_momayezi': total_momayezi,
        'projects': projects,
        'operators': operators,
        'operator_stats': operator_stats,
        'filter_project': filter_project,
        'filter_operator': filter_operator,
        'filter_status': filter_status,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
    }
    return render(request, 'core_admin/expert_dashboard.html', context)

# ==================== Feature Detail API ====================

@login_required
def feature_detail_api(request, feature_id):
    """API دریافت جزئیات قطعه برای مودال"""
    from .models import Feature

    feature = get_object_or_404(Feature, id=feature_id)

    # گرفتن مختصات از location
    lat = None
    lng = None
    if feature.location:
        lng = feature.location.x
        lat = feature.location.y

    data = {
        'id': feature.id,
        'feature_id': str(feature.feature_id) if feature.feature_id else str(feature.id),
        'project': feature.project.name if feature.project else 'بدون پروژه',
        'operator': feature.operator.get_full_name() or feature.operator.username if feature.operator else 'نامشخص',
        'latitude': lat,
        'longitude': lng,
        'land_use': feature.land_use,
        'area_sqm': feature.area_sqm,
        'owner_name': feature.owner_name,
        'address': feature.address,
        'description': feature.description,
        'recorded_at': feature.recorded_at.strftime('%Y/%m/%d %H:%M'),
        'status': feature.status,
        'status_display': feature.get_status_display(),
        'photo': feature.photo.url if feature.photo else None,
        'review_note': feature.review_note if hasattr(feature, 'review_note') else '',
    }
    return JsonResponse(data)

# ==================== Export GeoJSON ====================
@login_required
def export_geojson(request):
    """خروجی GeoJSON برای نمایش روی نقشه"""
    from .models import Feature, Project


    try:
        filter_project = request.GET.get('project')
        filter_operator = request.GET.get('operator')
        filter_status = request.GET.get('status')
        filter_date_from = request.GET.get('date_from')
        filter_date_to = request.GET.get('date_to')

        features = Feature.objects.all().select_related('project', 'operator')

        if filter_project:
            features = features.filter(project_id=filter_project)
        if filter_operator:
            features = features.filter(operator_id=filter_operator)
        if filter_status:
            features = features.filter(status=filter_status)
        if filter_date_from:
            features = features.filter(recorded_at__date__gte=filter_date_from)
        if filter_date_to:
            features = features.filter(recorded_at__date__lte=filter_date_to)

        geojson = {
            "type": "FeatureCollection",
            "features": []
        }

        for feature in features:
            # گرفتن مختصات از فیلد location (Point)
            lat = None
            lng = None

            if feature.location:
                # location از نوع Point است
                lng = feature.location.x  # طول جغرافیایی
                lat = feature.location.y  # عرض جغرافیایی

            if lat and lng:
                geojson["features"].append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lng), float(lat)]
                    },
                    "properties": {
                        "id": str(feature.feature_id) if feature.feature_id else str(feature.id),
                        "project_name": feature.project.name if feature.project else "",
                        "operator_name": feature.operator.get_full_name() or feature.operator.username if feature.operator else "",
                        "land_use": feature.land_use or "",
                        "area_sqm": str(feature.area_sqm) if feature.area_sqm else "",
                        "owner_name": feature.owner_name or "",
                        "address": feature.address or "",
                        "description": feature.description or "",
                        "status": feature.status,
                        "recorded_at": feature.recorded_at.isoformat() if feature.recorded_at else "",
                        "photo_url": feature.photo.url if feature.photo else "",
                    }
                })

        return JsonResponse(geojson, safe=False, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'features': []}, status=500)


    # ==================== Dashboard & Statistics ====================

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """داشبورد اصلی با آمار کامل"""
    # آمار پایه
    all_users = User.objects.filter(is_superuser=False)
    total_users = all_users.count()
    total_operators = User.objects.filter(groups__name='operator').count()
    total_experts = User.objects.filter(groups__name='expert').count()

    # آمار زمانی
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    new_users_today = User.objects.filter(date_joined__date=today).count()
    new_users_week = User.objects.filter(date_joined__date__gte=week_ago).count()

    # آمار وضعیت
    active_users = User.objects.filter(is_active=True, is_superuser=False).count()
    inactive_users = User.objects.filter(is_active=False, is_superuser=False).count()

    # دریافت تنظیمات صفحه‌بندی
    items_per_page = 10

    # صفحه‌بندی کاربران
    users_list = all_users.select_related().prefetch_related('groups').order_by('-date_joined')
    paginator = Paginator(users_list, items_per_page)
    page = request.GET.get('page', 1)

    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    stats = {
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'recent_logs_count': 0,
        'total_logs': 0,
    }

    context = {
        "users": users,
        "total_users": total_users,
        "total_operators": total_operators,
        "total_experts": total_experts,
        "stats": stats,
        "paginator": paginator,
    }
    return render(request, "core_admin/dashboard.html", context)


# ==================== User Management ====================

@login_required
@user_passes_test(is_admin)
def add_operator(request):
    """افزودن اپراتور جدید"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")

        if User.objects.filter(username=username).exists():
            return render(request, "core_admin/create_user.html", {
                "error": "این نام کاربری قبلاً ثبت شده است.",
                "page_title": "افزودن اپراتور",
                "button_text": "ایجاد اپراتور"
            })

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        group, _ = Group.objects.get_or_create(name="operator")
        user.groups.add(group)

        log_action(request, "افزودن اپراتور", f"افزودن اپراتور: {username}")
        messages.success(request, f"اپراتور {username} با موفقیت ایجاد شد.")
        return redirect("core_admin:dashboard")

    return render(request, "core_admin/create_user.html", {
        "page_title": "افزودن اپراتور",
        "button_text": "ایجاد اپراتور"
    })


@login_required
@user_passes_test(is_admin)
def add_expert(request):
    """افزودن کارشناس جدید"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")

        if User.objects.filter(username=username).exists():
            return render(request, "core_admin/create_user.html", {
                "error": "این نام کاربری قبلاً ثبت شده است.",
                "page_title": "افزودن کارشناس",
                "button_text": "ایجاد کارشناس"
            })

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        group, _ = Group.objects.get_or_create(name="expert")
        user.groups.add(group)

        log_action(request, "افزودن کارشناس", f"افزودن کارشناس: {username}")
        messages.success(request, f"کارشناس {username} با موفقیت ایجاد شد.")
        return redirect("core_admin:dashboard")

    return render(request, "core_admin/create_user.html", {
        "page_title": "افزودن کارشناس",
        "button_text": "ایجاد کارشناس"
    })


@login_required
@user_passes_test(is_admin)
def edit_user(request, user_id):
    """ویرایش اطلاعات کاربر"""
    user = get_object_or_404(User, id=user_id)

    if user.is_superuser:
        messages.error(request, "امکان ویرایش ادمین وجود ندارد")
        return redirect("core_admin:dashboard")

    if request.method == "POST":
        user.first_name = request.POST.get("first_name", "")
        user.last_name = request.POST.get("last_name", "")
        user.username = request.POST.get("username", "")
        user.email = request.POST.get("email", "")
        user.save()

        log_action(request, "ویرایش کاربر", f"ویرایش کاربر: {user.username}")
        messages.success(request, f"اطلاعات کاربر {user.username} با موفقیت ویرایش شد")
        return redirect("core_admin:dashboard")

    return render(request, "core_admin/edit_user.html", {"user": user})

@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    """حذف کاربر"""
    user = get_object_or_404(User, id=user_id)

    if user.is_superuser:
        messages.error(request, "امکان حذف ادمین وجود ندارد")
    elif user == request.user:
        messages.error(request, "امکان حذف کاربر خودتان وجود ندارد")
    else:
        username = user.get_full_name() or user.username
        log_action(request, "حذف کاربر", f"حذف کاربر: {username}")
        user.delete()
        messages.success(request, f"کاربر {username} با موفقیت حذف شد")

    return redirect("core_admin:dashboard")

@login_required
@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    """تغییر وضعیت فعال/غیرفعال کاربر"""
    user = get_object_or_404(User, id=user_id)

    if user.is_superuser:
        messages.error(request, "امکان تغییر وضعیت ادمین وجود ندارد")
    elif user == request.user:
        messages.error(request, "امکان تغییر وضعیت کاربر خودتان وجود ندارد")
    else:
        user.is_active = not user.is_active
        user.save()
        status = "فعال" if user.is_active else "غیرفعال"
        log_action(request, "تغییر وضعیت", f"تغییر وضعیت {user.username} به {status}")
        messages.success(request, f"وضعیت کاربر {user.username} به {status} تغییر کرد")

    return redirect("core_admin:dashboard")


@login_required
@user_passes_test(is_admin)
def change_role(request, user_id, role):
    """تغییر نقش کاربر"""
    user = get_object_or_404(User, id=user_id)

    if user.is_superuser:
        messages.error(request, "امکان تغییر نقش ادمین وجود ندارد")
        return redirect("core_admin:dashboard")

    # پاک کردن نقش‌های قبلی
    user.groups.clear()

    if role == "operator":
        group, _ = Group.objects.get_or_create(name="operator")
        user.groups.add(group)
        messages.success(request, f"{user.username} به اپراتور تبدیل شد")
        log_action(request, "تغییر نقش", f"تغییر نقش {user.username} به اپراتور")
    elif role == "expert":
        group, _ = Group.objects.get_or_create(name="expert")
        user.groups.add(group)
        messages.success(request, f"{user.username} به کارشناس تبدیل شد")
        log_action(request, "تغییر نقش", f"تغییر نقش {user.username} به کارشناس")
    elif role == "user":
        messages.success(request, f"نقش {user.username} حذف شد")
        log_action(request, "تغییر نقش", f"حذف نقش {user.username}")

    return redirect("core_admin:dashboard")


# ==================== Bulk Actions ====================

@login_required
@user_passes_test(is_admin)
def bulk_action(request):
    """عملیات گروهی روی کاربران"""
    if request.method == "POST":
        user_ids = request.POST.getlist('user_ids')
        action = request.POST.get('action')

        if not user_ids:
            messages.error(request, "هیچ کاربری انتخاب نشده است")
            return redirect("core_admin:dashboard")

        users = User.objects.filter(id__in=user_ids, is_superuser=False)
        users = users.exclude(id=request.user.id)
        count = users.count()

        if action == 'delete':
            usernames = list(users.values_list('username', flat=True))
            users.delete()
            messages.success(request, f"{len(usernames)} کاربر با موفقیت حذف شدند")
            log_action(request, "حذف گروهی", f"حذف کاربران: {', '.join(usernames)}")

        elif action == 'activate':
            count = users.update(is_active=True)
            messages.success(request, f"{count} کاربر فعال شدند")
            log_action(request, "فعال‌سازی گروهی", f"فعال‌سازی {count} کاربر")

        elif action == 'deactivate':
            count = users.update(is_active=False)
            messages.success(request, f"{count} کاربر غیرفعال شدند")
            log_action(request, "غیرفعال‌سازی گروهی", f"غیرفعال‌سازی {count} کاربر")

        elif action == 'make_operator':
            group, _ = Group.objects.get_or_create(name="operator")
            for user in users:
                user.groups.clear()
                user.groups.add(group)
            messages.success(request, f"{users.count()} کاربر به اپراتور تبدیل شدند")
            log_action(request, "تبدیل گروهی به اپراتور", f"تبدیل {users.count()} کاربر")

        elif action == 'make_expert':
            group, _ = Group.objects.get_or_create(name="expert")
            for user in users:
                user.groups.clear()
                user.groups.add(group)
            messages.success(request, f"{users.count()} کاربر به کارشناس تبدیل شدند")
            log_action(request, "تبدیل گروهی به کارشناس", f"تبدیل {users.count()} کاربر")

        elif action == 'remove_role':
            for user in users:
                user.groups.clear()
            messages.success(request, f"نقش {users.count()} کاربر حذف شد")
            log_action(request, "حذف نقش گروهی", f"حذف نقش {users.count()} کاربر")

    return redirect("core_admin:dashboard")


# ==================== Export ====================

@login_required
@user_passes_test(is_admin)
def export_users_csv(request):
    """خروجی گرفتن از کاربران به صورت CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'شناسه', 'نام کاربری', 'نام', 'نام خانوادگی', 'ایمیل',
        'نقش', 'تاریخ عضویت', 'آخرین ورود', 'وضعیت'
    ])

    users = User.objects.filter(is_superuser=False).order_by('-date_joined')

    for user in users:
        roles = ", ".join([g.name for g in user.groups.all()]) or "بدون نقش"

        # ترجمه نقش‌ها به فارسی
        role_map = {
            'operator': 'اپراتور',
            'expert': 'کارشناس',
        }
        for en, fa in role_map.items():
            roles = roles.replace(en, fa)

        writer.writerow([
            user.id,
            user.username,
            user.first_name or '',
            user.last_name or '',
            user.email or '',
            roles,
            user.date_joined.strftime('%Y/%m/%d %H:%M') if user.date_joined else '',
            user.last_login.strftime('%Y/%m/%d %H:%M') if user.last_login else '---',
            'فعال' if user.is_active else 'غیرفعال'
        ])

    log_action(request, "خروجی گرفتن", "خروجی CSV از تمام کاربران")
    messages.success(request, f"{users.count()} کاربر با موفقیت در فایل CSV ذخیره شدند")
    return response

# ==================== Profile ====================
@login_required
def profile(request):
    """صفحه پروفایل کاربر - هر کاربر فقط اطلاعات خودش را می‌بیند"""

    if request.method == "POST":
        if 'change_password' in request.POST:
            # تغییر رمز عبور
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if request.user.check_password(old_password):
                if new_password1 == new_password2:
                    if len(new_password1) >= 6:
                        request.user.set_password(new_password1)
                        request.user.save()
                        update_session_auth_hash(request, request.user)
                        log_action(request, "تغییر رمز عبور", "تغییر رمز عبور توسط کاربر")
                        messages.success(request, "رمز عبور با موفقیت تغییر کرد")
                    else:
                        messages.error(request, "رمز عبور جدید باید حداقل ۶ کاراکتر باشد")
                else:
                    messages.error(request, "رمز عبور جدید و تکرار آن مطابقت ندارند")
            else:
                messages.error(request, "رمز عبور فعلی اشتباه است")
        else:
            # تغییر اطلاعات پروفایل
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            email = request.POST.get('email', '')

            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.save()

            log_action(request, "بروزرسانی پروفایل", "بروزرسانی اطلاعات پروفایل")
            messages.success(request, "اطلاعات پروفایل با موفقیت بروزرسانی شد")

        return redirect("core_admin:profile")

    return render(request, "core_admin/profile.html", {"user": request.user})

# ==================== پروفایل کارشناس ====================
@login_required
def expert_profile_view(request):
    """پروفایل مخصوص کارشناس با قابلیت آپلود عکس"""
    if not request.user.groups.filter(name='expert').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:expert_login')

    # ایجاد پروفایل اگر وجود نداشت
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    # ========== پردازش درخواست AJAX برای آپلود عکس ==========
    if request.method == 'POST' and request.FILES.get('avatar'):
        try:
            # حذف عکس قدیمی اگر وجود داشت
            if profile.avatar:
                profile.avatar.delete()

            # ذخیره عکس جدید
            profile.avatar = request.FILES['avatar']
            profile.save()

            return JsonResponse({
                'success': True,
                'url': profile.avatar.url,
                'message': 'عکس پروفایل با موفقیت بروزرسانی شد'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # ========== پردازش درخواست عادی فرم ==========
    if request.method == 'POST':
        if 'change_password' in request.POST:
            # تغییر رمز عبور
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if request.user.check_password(old_password):
                if new_password1 == new_password2 and len(new_password1) >= 6:
                    request.user.set_password(new_password1)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "رمز عبور با موفقیت تغییر کرد")
                else:
                    messages.error(request, "رمز جدید معتبر نیست یا مطابقت ندارد")
            else:
                messages.error(request, "رمز عبور فعلی اشتباه است")
        else:
            # بروزرسانی اطلاعات
            request.user.first_name = request.POST.get('first_name', '')
            request.user.last_name = request.POST.get('last_name', '')
            request.user.email = request.POST.get('email', '')
            request.user.save()

            # بروزرسانی پروفایل
            profile.phone = request.POST.get('phone', '')
            profile.bio = request.POST.get('bio', '')

            profile.save()
            messages.success(request, "اطلاعات پروفایل با موفقیت بروزرسانی شد")

        return redirect('core_admin:expert_profile')

    context = {
        'user': request.user,
        'profile': profile,
    }
    return render(request, 'core_admin/expert_profile.html', context)

# ==================== Logs (نسخه موقت) ====================

@login_required
@user_passes_test(is_admin)
def view_logs(request):
    """مشاهده لاگ‌های سیستم (نسخه موقت)"""
    messages.info(request, "سیستم لاگ‌ها در حال راه‌اندازی است. برای مشاهده لاگ‌های کامل بعداً مراجعه کنید.")
    return render(request, "core_admin/logs.html", {"logs": []})


# ==================== Settings (نسخه موقت) ====================

@login_required
@user_passes_test(is_admin)
def settings_view(request):
    """صفحه تنظیمات سیستم"""
    if request.method == "POST":
        items_per_page = request.POST.get('items_per_page', '10')
        theme = request.POST.get('theme', 'light')

        # ذخیره در session
        request.session['items_per_page'] = items_per_page
        request.session['theme'] = theme

        log_action(request, "بروزرسانی تنظیمات", "بروزرسانی تنظیمات سیستم")
        messages.success(request, "تنظیمات با موفقیت ذخیره شد")
        return redirect("core_admin:settings")

    settings = {
        'items_per_page': request.session.get('items_per_page', '10'),
        'theme': request.session.get('theme', 'light'),
    }

    return render(request, "core_admin/settings.html", {"settings": settings})


# ==================== Search API ====================

@login_required
@user_passes_test(is_admin)
def search_users_api(request):
    """API جستجوی کاربران (برای استفاده AJAX)"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse([], safe=False)

    users = User.objects.filter(
        Q(is_superuser=False) &
        (Q(username__icontains=query) |
         Q(first_name__icontains=query) |
         Q(last_name__icontains=query) |
         Q(email__icontains=query))
    )[:20]

    results = []
    for user in users:
        results.append({
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'is_active': user.is_active,
            'roles': [g.name for g in user.groups.all()]
        })

    return JsonResponse(results, safe=False)


# ==================== Logout ====================
@login_required
def admin_logout(request):
    """خروج از سیستم و هدایت به صفحه اصلی"""

    # خروج از سیستم
    logout(request)

    # پاک کردن کامل سشن
    request.session.flush()

    # ریدایرکت به صفحه اصلی
    response = HttpResponseRedirect('/')

    # هدرهای جلوگیری از کش شدن
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response
# ==================== Operator Panel ====================
@login_required
def operator_dashboard(request):
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "شما دسترسی به این بخش را ندارید.")
        return redirect('core_admin:operator_login')

    from .models import Project, Feature

    default_project, created = Project.objects.get_or_create(
        name="پروژه پیش‌فرض",
        defaults={'description': "پروژه اصلی نقشه‌برداری", 'created_by': request.user}
    )

    projects = Project.objects.filter(is_active=True)
    user_features = Feature.objects.filter(operator=request.user).order_by('-recorded_at')[:50]

    if request.method == 'POST':
        try:
            project_id = request.POST.get('project')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            land_use = request.POST.get('land_use', '')
            area = request.POST.get('area', '')
            owner_name = request.POST.get('owner_name', '')
            address = request.POST.get('address', '')
            description = request.POST.get('description', '')

            if not project_id:
                project_id = default_project.id

            if not latitude or not longitude:
                messages.error(request, "لطفاً موقعیت مکانی را مشخص کنید.")
                return redirect('core_admin:operator_dashboard')

            # ایجاد نقطه مکانی با PostGIS
            location = Point(float(longitude), float(latitude), srid=4326)

            feature = Feature.objects.create(
                project_id=project_id,
                operator=request.user,
                location=location,
                land_use=land_use,
                area_sqm=float(area) if area else None,
                owner_name=owner_name,
                address=address,
                description=description,
                status='submitted'
            )

            if request.FILES.get('photo'):
                feature.photo = request.FILES['photo']
                feature.save()

            messages.success(request, "قطعه با موفقیت ثبت و برای بررسی ارسال شد.")
            return redirect('core_admin:operator_dashboard')

        except Exception as e:
            messages.error(request, f"خطا در ثبت: {str(e)}")
            return redirect('core_admin:operator_dashboard')

    context = {
        'user': request.user,
        'projects': projects,
        'user_features': user_features,
        'default_project_id': default_project.id,
    }
    return render(request, 'core_admin/operator_dashboard.html', context)

# ==================== Expert Panel ====================

def check_user_role(request):
    """بررسی نقش کاربر فعلی"""
    if not request.user.is_authenticated:
        return JsonResponse({'role': 'none'})

    if request.user.groups.filter(name='operator').exists():
        return JsonResponse({'role': 'operator'})
    elif request.user.groups.filter(name='expert').exists():
        return JsonResponse({'role': 'expert'})
    elif request.user.is_staff:
        return JsonResponse({'role': 'admin'})
    else:
        return JsonResponse({'role': 'none'})

def check_session(request):
    if request.user.is_authenticated:
        return JsonResponse({'is_logged_in': True})
    return JsonResponse({'is_logged_in': False})


def check_role_redirect(request):
    """بررسی نقش کاربر و هدایت به پنل مناسب"""
    if not request.user.is_authenticated:
        return redirect('core_admin:login')

    if request.user.groups.filter(name='operator').exists():
        return redirect('core_admin:operator_dashboard')
    elif request.user.groups.filter(name='expert').exists():
        return redirect('core_admin:expert_dashboard')
    elif request.user.is_staff:
        return redirect('core_admin:dashboard')
    else:
        return redirect('core_admin:login')

@csrf_exempt
@login_required
def update_feature_status(request, feature_id):
    """بروزرسانی وضعیت قطعه توسط کارشناس با ذخیره دلیل رد"""
    from .models import Feature
    import json

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            status = data.get('status')
            review_note = data.get('review_note', '')

            feature = get_object_or_404(Feature, id=feature_id)
            feature.status = status
            feature.review_note = review_note
            feature.reviewed_by = request.user
            feature.reviewed_at = timezone.now()
            feature.save()

            # پیام برای ترمینال
            print(f"[LOG] قطعه {feature.feature_id} توسط {request.user.username} به وضعیت {status} تغییر کرد. نظر: {review_note}")

            return JsonResponse({'success': True, 'message': 'وضعیت با موفقیت تغییر کرد'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid method'})

# ==================== Operator Profile ====================



@login_required
def operator_change_password(request):
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        if request.user.check_password(old_password):
            if new_password1 == new_password2 and len(new_password1) >= 6:
                request.user.set_password(new_password1)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "رمز عبور با موفقیت تغییر کرد")
                return redirect('core_admin:operator_profile')
            else:
                messages.error(request, "رمز جدید معتبر نیست یا مطابقت ندارد")
        else:
            messages.error(request, "رمز عبور فعلی اشتباه است")

    return render(request, 'core_admin/operator_change_password.html')


@login_required
def operator_add_feature(request):
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    from .models import Project, Feature
    from django.contrib.gis.geos import Point

    projects = Project.objects.filter(is_active=True)

    if request.method == 'POST':
        try:
            project_id = request.POST.get('project')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            land_use = request.POST.get('land_use', '')
            area = request.POST.get('area', '')
            owner_name = request.POST.get('owner_name', '')
            address = request.POST.get('address', '')
            description = request.POST.get('description', '')

            if not latitude or not longitude:
                messages.error(request, "لطفاً موقعیت مکانی را مشخص کنید")
                return redirect('core_admin:operator_add_feature')

            location = Point(float(longitude), float(latitude), srid=4326)

            # ✅ ذخیره خروجی در متغیر feature
            feature = Feature.objects.create(
                project_id=project_id,
                operator=request.user,
                location=location,
                land_use=land_use,
                area_sqm=float(area) if area else None,
                owner_name=owner_name,
                address=address,
                description=description,
                status='submitted'
            )

            # ✅ حالا feature تعریف شده و می‌توانیم عکس را اضافه کنیم
            if request.FILES.get('photo'):
                feature.photo = request.FILES['photo']
                feature.save()

            messages.success(request, "قطعه با موفقیت ثبت شد")
            return redirect('core_admin:operator_my_features')

        except Exception as e:
            messages.error(request, f"خطا: {str(e)}")

    return render(request, 'core_admin/operator_add_feature.html', {'projects': projects})


@login_required
def operator_my_features(request):
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    from .models import Feature

    features = Feature.objects.filter(operator=request.user).order_by('-recorded_at')

    return render(request, 'core_admin/operator_my_features.html', {'features': features})

# ========== داشبورد اپراتور ==========
@login_required
def operator_home(request):
    """داشبورد اصلی اپراتور - فقط نمایش طرح‌های شهری"""
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    from .models import ProjectPlan

    # آمار طرح‌ها
    total_plans = ProjectPlan.objects.filter(operator=request.user).count()
    pending_plans = ProjectPlan.objects.filter(operator=request.user, status='pending').count()
    approved_plans = ProjectPlan.objects.filter(operator=request.user, status='approved').count()
    rejected_plans = ProjectPlan.objects.filter(operator=request.user, status='rejected').count()

    # آخرین طرح‌های ثبت شده
    recent_plans = ProjectPlan.objects.filter(operator=request.user).select_related(
        'tafsili_plan', 'momayezi_plan'
    ).order_by('-created_at')[:5]

    context = {
        'total_plans': total_plans,
        'pending_plans': pending_plans,
        'approved_plans': approved_plans,
        'rejected_plans': rejected_plans,
        'recent_plans': recent_plans,
    }
    return render(request, 'core_admin/operator_home.html', context)


@login_required
def operator_momayezi(request):
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    if request.method == 'POST':
        from .models import MomayeziData  # اسم مدلت رو چک کن
        data = MomayeziData.objects.create(
            operator=request.user,
            subject=request.POST.get('subject'),
            description=request.POST.get('description')
        )
        if request.FILES.get('attachment'):
            data.attachment = request.FILES['attachment']
            data.save()
        messages.success(request, "اطلاعات طرح موضوعی با موفقیت ذخیره شد.")
        return redirect('core_admin:operator_momayezi')

    return render(request, 'core_admin/operator_momayezi.html')


# ==================== مشاهده اطلاعات طرح‌ها توسط کارشناس ====================

@login_required
def expert_tafsili_list(request):
    """مشاهده لیست اطلاعات طرح تفصیلی/جامع ثبت شده توسط اپراتورها"""
    if not request.user.groups.filter(name='expert').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:expert_login')

    from .models import ProjectPlan
    from django.contrib.auth.models import User
    from django.core.paginator import Paginator

    filter_operator = request.GET.get('operator')
    filter_project = request.GET.get('project')
    filter_status = request.GET.get('status')

    # ✅ همه طرح‌ها (بدون فیلتر status)
    data_list = ProjectPlan.objects.filter(
        plan_type='tafsili'
    ).select_related('operator', 'tafsili_plan').order_by('-created_at')

    # اعمال فیلترها
    if filter_operator:
        data_list = data_list.filter(operator_id=filter_operator)
    if filter_project:
        data_list = data_list.filter(title__icontains=filter_project)
    if filter_status:
        data_list = data_list.filter(status=filter_status)

    # صفحه‌بندی
    paginator = Paginator(data_list, 20)
    page = request.GET.get('page', 1)
    data_page = paginator.get_page(page)

    operators = User.objects.filter(groups__name='operator')

    context = {
        'data_list': data_page,
        'operators': operators,
        'filter_operator': filter_operator,
        'filter_project': filter_project,
        'filter_status': filter_status,
        'title': 'طرح تفصیلی / جامع',
        'type': 'tafsili',
    }
    return render(request, 'core_admin/expert_plans_list_new.html', context)


@login_required
def expert_review_plan(request, plan_id):
    """بررسی طرح توسط کارشناس با امکان تأیید/رد و ثبت دلیل"""
    if not request.user.groups.filter(name='expert').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:expert_login')

    from .models import (
        ProjectPlan, TafsiliPlanData,  MomayeziPlanData,
        FinalTafsiliData, FinalMomayeziData, PlanRevisionHistory
    )

    plan = get_object_or_404(ProjectPlan, id=plan_id)

    # دریافت اطلاعات اختصاصی بر اساس نوع طرح
    plan_data = None
    if plan.plan_type == 'tafsili':
        plan_data = getattr(plan, 'tafsili_plan', None)
    elif plan.plan_type == 'momayezi':
        plan_data = getattr(plan, 'momayezi_plan', None)

    if request.method == 'POST':
        action = request.POST.get('action')
        expert_note = request.POST.get('expert_note', '')

        if action == 'approve':
            # ========== ذخیره در دیتابیس نهایی ==========
            try:
                # بررسی اینکه قبلاً ذخیره نشده باشد
                if plan.plan_type == 'tafsili' and plan_data and not hasattr(plan, 'final_tafsili'):
                    FinalTafsiliData.objects.create(
                        plan=plan,
                        zone_code=plan_data.zone_code,
                        land_use_type=plan_data.land_use_type,
                        detailed_use=plan_data.detailed_use,
                        density=plan_data.density,
                        floor_limit=plan_data.floor_limit,
                        street_name=plan_data.street_name,
                        street_width=plan_data.street_width,
                        ownership_type=plan_data.ownership_type,
                        building_age=plan_data.building_age,
                        facade_type=plan_data.facade_type,
                        material_type=plan_data.material_type,
                        building_quality=plan_data.building_quality,
                        functional_level=plan_data.functional_level,
                        upper_floor_use=plan_data.upper_floor_use,
                        ground_floor_use=plan_data.ground_floor_use,
                        dominant_use=plan_data.dominant_use,
                        built_area=plan_data.built_area,
                        land_area=plan_data.land_area,
                        neighborhood=plan_data.neighborhood,
                        parcel_code=plan_data.parcel_code,
                        photo=plan_data.photo
                    )
                    messages.success(request, "✅ طرح تفصیلی تأیید و در پایگاه داده ذخیره شد.")

                elif plan.plan_type == 'momayezi' and plan_data and not hasattr(plan, 'final_momayezi'):
                    FinalMomayeziData.objects.create(
                        plan=plan,
                        parcel_code=plan_data.parcel_code,
                        ownership_type=plan_data.ownership_type,
                        owner_name=plan_data.owner_name,
                        building_type=plan_data.building_type,
                        area=plan_data.area,
                        construction_year=plan_data.construction_year,
                        is_licensed=plan_data.is_licensed,
                        attachment=plan_data.attachment
                    )
                    messages.success(request, "✅ ممیزی املاک تأیید و در پایگاه داده ذخیره شد.")
                else:
                    messages.info(request, "ℹ️ این طرح قبلاً در دیتابیس نهایی ذخیره شده است.")

                # به‌روزرسانی وضعیت طرح اصلی
                plan.status = 'approved'
                plan.expert = request.user
                plan.expert_note = expert_note
                plan.is_final = True
                plan.save()

            except Exception as e:
                messages.error(request, f"❌ خطا در ذخیره‌سازی: {str(e)}")
                return redirect('core_admin:expert_review_plan', plan_id=plan_id)

        elif action == 'reject':
            # رد طرح - بررسی وجود توضیحات
            if not expert_note.strip():
                messages.error(request, "⚠️ لطفاً دلیل رد طرح را وارد کنید.")
                return redirect('core_admin:expert_review_plan', plan_id=plan_id)

            plan.status = 'rejected'
            plan.expert = request.user
            plan.expert_note = expert_note
            plan.is_final = False
            plan.revision_count += 1

            # ثبت تاریخچه اصلاح
            PlanRevisionHistory.objects.create(
                plan=plan,
                revision_number=plan.revision_count,
                operator_data={},
                expert_note=expert_note
            )

            plan.save()
            messages.warning(request, "❌ طرح رد شد. نظر شما به اپراتور منتقل گردید.")

        return redirect('core_admin:expert_pending_plans')

    context = {
        'plan': plan,
        'plan_data': plan_data,
    }
    return render(request, 'core_admin/expert_review_plan.html', context)
# ==================== پنل اپراتور - ثبت طرح‌ها ====================

@login_required
def operator_select_plan(request):
    """صفحه انتخاب نوع طرح برای ثبت"""
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    return render(request, 'core_admin/operator_select_plan.html')


@login_required
def operator_submit_tafsili(request):
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    from .models import ProjectPlan, TafsiliPlanData
    from django.contrib.gis.geos import Point

    if request.method == 'POST':
        try:
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')

            location = None
            if latitude and longitude:
                try:
                    location = Point(float(longitude), float(latitude), srid=4326)
                except:
                    pass

            plan = ProjectPlan.objects.create(
                plan_type='tafsili',
                operator=request.user,
                title=request.POST.get('title', ''),
                description=request.POST.get('description', ''),
                status='pending'
            )

            tafsili = TafsiliPlanData.objects.create(
                plan=plan,
                location=location,
                # ========== اطلاعات پایه ==========
                parcel_code=request.POST.get('parcel_code', ''),
                zone_code=request.POST.get('zone_code', ''),
                land_use_type=request.POST.get('land_use_type', ''),  # ← این خط مهمه
                neighborhood=request.POST.get('neighborhood', ''),
                detailed_use=request.POST.get('detailed_use', ''),
                # ========== اطلاعات شهری ==========
                street_name=request.POST.get('street_name', ''),
                street_width=request.POST.get('street_width') or None,
                ownership_type=request.POST.get('ownership_type', ''),
                land_area=request.POST.get('land_area') or None,
                # ========== اطلاعات ساختمانی ==========
                density=request.POST.get('density') or None,
                floor_limit=request.POST.get('floor_limit') or None,
                built_area=request.POST.get('built_area') or None,
                building_age=request.POST.get('building_age', ''),
                facade_type=request.POST.get('facade_type', ''),
                material_type=request.POST.get('material_type', ''),
                building_quality=request.POST.get('building_quality', ''),
                functional_level=request.POST.get('functional_level', ''),
                # ========== فیلدهای جدید ==========
                floor_count=request.POST.get('floor_count') or None,
                occupancy_rate=request.POST.get('occupancy_rate') or None,
                building_status=request.POST.get('building_status', ''),
                # ========== اطلاعات کاربری ==========
                upper_floor_use=request.POST.get('upper_floor_use', ''),
                ground_floor_use=request.POST.get('ground_floor_use', ''),
                dominant_use=request.POST.get('dominant_use', ''),
            )

            if request.FILES.get('photo'):
                tafsili.photo = request.FILES['photo']
                tafsili.save()

            messages.success(request, "✅ طرح تفصیلی با موفقیت ارسال شد.")
            return redirect('core_admin:operator_my_plans')

        except Exception as e:
            messages.error(request, f"❌ خطا در ثبت: {str(e)}")
            return redirect('core_admin:operator_submit_tafsili')

    return render(request, 'core_admin/operator_submit_tafsili.html')

@login_required
def operator_submit_momayezi(request):
    """ثبت ممیزی املاک"""
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    from .models import ProjectPlan, MomayeziData

    if request.method == 'POST':
        try:
            plan = ProjectPlan.objects.create(
                plan_type='momayezi',
                operator=request.user,
                title=request.POST.get('title'),
                description=request.POST.get('description', ''),
                status='pending'
            )

            momayezi = MomayeziData.objects.create(
                plan=plan,
                parcel_code=request.POST.get('parcel_code'),
                ownership_type=request.POST.get('ownership_type'),
                owner_name=request.POST.get('owner_name'),
                building_type=request.POST.get('building_type'),
                area=float(request.POST.get('area')),
                construction_year=int(request.POST.get('construction_year')),
                is_licensed=request.POST.get('is_licensed') == 'on'
            )

            if request.FILES.get('attachment'):
                momayezi.attachment = request.FILES['attachment']
                momayezi.save()

            messages.success(request, "ممیزی املاک با موفقیت ارسال شد. منتظر تأیید کارشناس باشید.")
            return redirect('core_admin:operator_my_plans')

        except Exception as e:
            messages.error(request, f"خطا در ثبت: {str(e)}")

    return render(request, 'core_admin/operator_submit_momayezi.html')


@login_required
def operator_my_plans(request):
    """مشاهده طرح‌های ارسالی اپراتور"""
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    from .models import ProjectPlan

    # ✅ مطمئن شو operator=request.user درسته
    plans = ProjectPlan.objects.filter(
        operator=request.user,  # ← این خط باید درست باشه
        plan_type='tafsili'
    ).select_related('tafsili_plan').order_by('-created_at')

    total_count = plans.count()
    pending_count = plans.filter(status='pending').count()
    approved_count = plans.filter(status='approved').count()
    rejected_count = plans.filter(status='rejected').count()

    context = {
        'plans': plans,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'core_admin/operator_my_plans.html', context)
# ==================== پنل کارشناس - بررسی طرح‌ها ====================

@login_required
def expert_pending_plans(request):
    """لیست طرح‌های در انتظار بررسی (فقط طرح‌هایی که هنوز تأیید/رد نشده‌اند)"""
    if not request.user.groups.filter(name='expert').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:expert_login')

    from .models import ProjectPlan

    # فقط طرح‌هایی که وضعیت pending دارند
    pending_plans = ProjectPlan.objects.filter(
        status='pending'
    ).select_related('operator', 'tafsili_plan', 'momayezi_plan').order_by('-created_at')

    return render(request, 'core_admin/expert_pending_plans.html', {'plans': pending_plans})


@login_required
def expert_revised_plans(request):
    """لیست طرح‌های اصلاح شده توسط اپراتور (در انتظار بررسی مجدد)"""
    if not request.user.groups.filter(name='expert').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:expert_login')

    from .models import ProjectPlan

    revised_plans = ProjectPlan.objects.filter(status='revised').order_by('-updated_at')

    return render(request, 'core_admin/expert_revised_plans.html', {'plans': revised_plans})

@login_required
def expert_approved_plans(request):
    """لیست طرح‌های تأیید شده نهایی (فقط نمایش داده می‌شوند)"""
    if not request.user.groups.filter(name='expert').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:expert_login')

    from .models import ProjectPlan

    approved_plans = ProjectPlan.objects.filter(
        status='approved',
        is_final=True
    ).select_related('operator', 'final_tafsili', 'final_momayezi').order_by('-created_at')

    return render(request, 'core_admin/expert_approved_plans.html', {'plans': approved_plans})

@login_required
def operator_revise_plan(request, plan_id):
    """اصلاح طرح توسط اپراتور پس از دریافت نظر کارشناس"""
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    from .models import ProjectPlan, TafsiliPlanData, MomayeziPlanData

    plan = get_object_or_404(ProjectPlan, id=plan_id, operator=request.user)

    if plan.status != 'rejected':
        messages.error(request, "این طرح قابل اصلاح نیست")
        return redirect('core_admin:operator_my_plans')

    if request.method == 'POST':
        try:
            # به‌روزرسانی اطلاعات مشترک
            plan.title = request.POST.get('title')
            plan.description = request.POST.get('description', '')
            plan.status = 'pending'  # برگشت به حالت در انتظار
            plan.save()

            # به‌روزرسانی اطلاعات اختصاصی
            if plan.plan_type == 'tafsili':
                tafsili = plan.tafsili_plan
                tafsili.zone_code = request.POST.get('zone_code')
                tafsili.land_use_type = request.POST.get('land_use_type')
                tafsili.detailed_use = request.POST.get('detailed_use')
                tafsili.density = float(request.POST.get('density'))
                tafsili.floor_limit = int(request.POST.get('floor_limit'))
                if request.FILES.get('photo'):
                    tafsili.photo = request.FILES['photo']
                tafsili.save()

            elif plan.plan_type == 'momayezi':
                momayezi = plan.momayezi_plan
                momayezi.parcel_code = request.POST.get('parcel_code')
                momayezi.ownership_type = request.POST.get('ownership_type')
                momayezi.owner_name = request.POST.get('owner_name')
                momayezi.building_type = request.POST.get('building_type')
                momayezi.area = float(request.POST.get('area'))
                momayezi.construction_year = int(request.POST.get('construction_year'))
                momayezi.is_licensed = request.POST.get('is_licensed') == 'on'
                if request.FILES.get('attachment'):
                    momayezi.attachment = request.FILES['attachment']
                momayezi.save()

            messages.success(request, "طرح با موفقیت اصلاح و برای بررسی مجدد ارسال شد.")
            return redirect('core_admin:operator_my_plans')

        except Exception as e:
            messages.error(request, f"خطا در اصلاح: {str(e)}")

    context = {
        'plan': plan,
    }
    return render(request, 'core_admin/operator_revise_plan.html', context)

# ==================== Export Functions (CSV) ====================




@login_required
def export_final_detailed_csv(request):
    """خروجی CSV کامل با استفاده از کوئری مستقیم SQL"""

    if not (request.user.groups.filter(name='expert').exists() or request.user.is_staff):
        return redirect('core_admin:login')

    # کوئری مستقیم SQL با COALESCE برای فیلدهایی که ممکنه NULL باشن
    query = """
        SELECT 
            f.id AS "شناسه",
            p.title AS "عنوان پروژه",
            u.username AS "اپراتور",
            'تأیید شده' AS "وضعیت",
            TO_CHAR(p.created_at, 'YYYY/MM/DD HH24:MI') AS "تاریخ ثبت",
            TO_CHAR(f.created_at, 'YYYY/MM/DD HH24:MI') AS "تاریخ تأیید",
            f.zone_code AS "کد منطقه",
            f.neighborhood AS "نام محله",
            f.detailed_use AS "کاربری تفصیلی",
            f.street_name AS "نام معبر",
            f.street_width AS "عرض معبر (متر)",
            f.ownership_type AS "نوع مالکیت",
            f.land_area AS "مساحت عرصه (متر مربع)",
            f.built_area AS "مساحت اعیانی (متر مربع)",
            COALESCE(f.floor_count, t.floor_count) AS "تعداد طبقات",
            COALESCE(f.occupancy_rate, t.occupancy_rate) AS "سطح اشغال (%)",
            f.density AS "تراکم ساختمانی",
            f.floor_limit AS "حداکثر طبقات مجاز",
            f.building_age AS "قدمت بنا",
            f.facade_type AS "نوع نما",
            f.material_type AS "مصالح ساختمانی",
            f.building_quality AS "کیفیت ابنیه",
            f.functional_level AS "سطح عملکردی",
            f.upper_floor_use AS "کاربری طبقات بالای همکف",
            f.ground_floor_use AS "کاربری همکف",
            f.dominant_use AS "انواع کاربری (غالب)",
            COALESCE(f.description, p.description) AS "توضیحات",
            COALESCE(f.latitude, ST_Y(t.location)) AS "عرض جغرافیایی",
            COALESCE(f.longitude, ST_X(t.location)) AS "طول جغرافیایی"
        FROM core_admin_finaltafsilidata f
        INNER JOIN core_admin_projectplan p ON f.plan_id = p.id
        INNER JOIN auth_user u ON p.operator_id = u.id
        LEFT JOIN core_admin_tafsiliplandata t ON t.plan_id = p.id
        WHERE p.status = 'approved'
          AND p.plan_type = 'tafsili'
        ORDER BY f.created_at DESC
    """

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="export_final_tafsili.csv"'

    writer = csv.writer(response)

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)

    return response

@login_required
def expert_momayezi_list(request):
    """مشاهده لیست اطلاعات ممیزی املاک ثبت شده توسط اپراتورها"""
    if not request.user.groups.filter(name='expert').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:expert_login')

    from .models import ProjectPlan
    from django.contrib.auth.models import User
    from django.core.paginator import Paginator

    filter_operator = request.GET.get('operator')
    filter_project = request.GET.get('project')
    filter_status = request.GET.get('status')

    # دریافت طرح‌های ممیزی از مدل ProjectPlan
    data_list = ProjectPlan.objects.filter(
        plan_type='momayezi'
    ).select_related('operator', 'momayezi_plan').order_by('-created_at')

    if filter_operator:
        data_list = data_list.filter(operator_id=filter_operator)
    if filter_project:
        data_list = data_list.filter(title__icontains=filter_project)
    if filter_status:
        data_list = data_list.filter(status=filter_status)

    paginator = Paginator(data_list, 20)
    page = request.GET.get('page', 1)
    data_page = paginator.get_page(page)

    operators = User.objects.filter(groups__name='operator')

    context = {
        'data_list': data_page,
        'operators': operators,
        'filter_operator': filter_operator,
        'filter_project': filter_project,
        'filter_status': filter_status,
        'title': 'ممیزی املاک',
        'type': 'momayezi',
    }
    return render(request, 'core_admin/expert_plans_list_new.html', context)

@login_required
def expert_stats_dashboard(request):
    """داشبورد آماری پیشرفته برای کارشناسان"""
    if not request.user.groups.filter(name='expert').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:expert_login')

    from .models import Feature, ProjectPlan
    from django.db.models import Count
    from datetime import datetime, timedelta
    import calendar


    # آمار کلی قطعات
    total_features = Feature.objects.count()
    approved_features = Feature.objects.filter(status='approved').count()
    rejected_features = Feature.objects.filter(status='rejected').count()
    pending_features = Feature.objects.filter(status='submitted').count()

    # آمار کلی طرح‌ها
    total_plans = ProjectPlan.objects.count()
    approved_plans = ProjectPlan.objects.filter(status='approved').count()
    rejected_plans = ProjectPlan.objects.filter(status='rejected').count()
    pending_plans = ProjectPlan.objects.filter(status='pending').count()

    # آمار ماهانه (برای نمودار)
    monthly_stats = []
    current_year = datetime.now().year
    for month in range(1, 13):
        month_name = calendar.month_name[month]
        count = Feature.objects.filter(recorded_at__year=current_year, recorded_at__month=month).count()
        monthly_stats.append({
            'month': month_name,
            'count': count
        })

    context = {
        'total_features': total_features,
        'approved_features': approved_features,
        'rejected_features': rejected_features,
        'pending_features': pending_features,
        'total_plans': total_plans,
        'approved_plans': approved_plans,
        'rejected_plans': rejected_plans,
        'pending_plans': pending_plans,
        'monthly_stats': monthly_stats,
    }
    return render(request, 'core_admin/expert_stats.html', context)

@login_required
def expert_plan_detail_api(request, plan_id):
    from .models import ProjectPlan
    plan = get_object_or_404(ProjectPlan, id=plan_id)

    data = {
        'id': str(plan.id),
        'project': plan.title,
        'operator': plan.operator.get_full_name() or plan.operator.username,
        'recorded_at': plan.created_at.strftime('%Y/%m/%d %H:%M'),
        'status': plan.status,
        'review_note': plan.expert_note,
    }

    if hasattr(plan, 'tafsili_plan'):
        t = plan.tafsili_plan
        data.update({
            'parcel_code': t.parcel_code or '-',
            'zone_code': t.zone_code or '-',
            'land_use_type': t.land_use_type or '-',
            'neighborhood': t.neighborhood or '-',
            'detailed_use': t.detailed_use or '-',
            'street_name': t.street_name or '-',
            'street_width': t.street_width or '-',
            'ownership_type': t.ownership_type or '-',
            'land_area': t.land_area or '-',
            'built_area': t.built_area or '-',
            'occupancy_rate': t.occupancy_rate or '-',
            'floor_count': t.floor_count or '-',
            'floor_limit': t.floor_limit or '-',
            'density': t.density or '-',
            'building_age': t.building_age or '-',
            'facade_type': t.facade_type or '-',
            'material_type': t.material_type or '-',
            'building_quality': t.building_quality or '-',
            'functional_level': t.functional_level or '-',
            'upper_floor_use': t.upper_floor_use or '-',
            'ground_floor_use': t.ground_floor_use or '-',
            'dominant_use': t.dominant_use or '-',
            'building_status': t.building_status or '-',
            'photo': t.photo.url if t.photo else None,
            'latitude': t.location.y if t.location else None,
            'longitude': t.location.x if t.location else None,
        })

    return JsonResponse(data)


@csrf_exempt
@login_required
def expert_update_plan_status(request, plan_id):
    """بروزرسانی وضعیت طرح توسط کارشناس"""
    if not request.user.groups.filter(name='expert').exists():
        return JsonResponse({'success': False, 'error': 'دسترسی غیرمجاز'})

    from .models import ProjectPlan, FinalTafsiliData, FinalMomayeziData

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            status = data.get('status')
            review_note = data.get('review_note', '')

            plan = get_object_or_404(ProjectPlan, id=plan_id)

            if status == 'approved':
                if plan.plan_type == 'tafsili' and hasattr(plan, 'tafsili_plan'):
                    t = plan.tafsili_plan

                    # حذف نسخه قبلی
                    FinalTafsiliData.objects.filter(plan=plan).delete()

                    # ایجاد نسخه نهایی با تمام فیلدها
                    final = FinalTafsiliData.objects.create(
                        plan=plan,
                        # اطلاعات پایه
                        zone_code=t.zone_code or '',
                        neighborhood=t.neighborhood or '',
                        detailed_use=t.detailed_use or '',
                        # اطلاعات شهری
                        street_name=t.street_name or '',
                        street_width=t.street_width,
                        ownership_type=t.ownership_type or '',
                        land_area=t.land_area,
                        # اطلاعات ساختمانی
                        density=t.density,
                        floor_limit=t.floor_limit,
                        built_area=t.built_area,
                        building_age=t.building_age or '',
                        facade_type=t.facade_type or '',
                        material_type=t.material_type or '',
                        building_quality=t.building_quality or '',
                        functional_level=t.functional_level or '',
                        floor_count=t.floor_count,  # ✅ تعداد طبقات
                        occupancy_rate=t.occupancy_rate,  # ✅ سطح اشغال
                        building_status=t.building_status or '',
                        # اطلاعات کاربری
                        upper_floor_use=t.upper_floor_use or '',
                        ground_floor_use=t.ground_floor_use or '',
                        dominant_use=t.dominant_use or '',
                        description=plan.description or '',  # ✅ توضیحات
                        # عکس و موقعیت
                        photo=t.photo,
                        location=t.location,
                        latitude=t.location.y if t.location else None,  # ✅ عرض
                        longitude=t.location.x if t.location else None,  # ✅ طول
                    )

                elif plan.plan_type == 'momayezi' and hasattr(plan, 'momayezi_plan'):
                    FinalMomayeziData.objects.get_or_create(
                        plan=plan,
                        defaults={
                            'parcel_code': plan.momayezi_plan.parcel_code,
                            'ownership_type': plan.momayezi_plan.ownership_type,
                            'owner_name': plan.momayezi_plan.owner_name,
                            'building_type': plan.momayezi_plan.building_type,
                            'area': plan.momayezi_plan.area,
                            'construction_year': plan.momayezi_plan.construction_year,
                            'is_licensed': plan.momayezi_plan.is_licensed,
                            'attachment': plan.momayezi_plan.attachment
                        }
                    )

                plan.status = 'approved'
                plan.expert = request.user
                plan.expert_note = review_note
                plan.is_final = True
                plan.save()

            elif status == 'rejected':
                plan.status = 'rejected'
                plan.expert = request.user
                plan.expert_note = review_note
                plan.is_final = False
                plan.save()

            return JsonResponse({'success': True})

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid method'})

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'پروفایل'


class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ('username', 'get_full_name', 'email', 'get_role', 'is_active')
    list_filter = ('groups', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    def get_role(self, obj):
        if obj.groups.filter(name='operator').exists():
            return 'اپراتور'
        elif obj.groups.filter(name='expert').exists():
            return 'کارشناس'
        elif obj.is_staff:
            return 'ادمین'
        return 'کاربر عادی'

    get_role.short_description = 'نقش'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@login_required
def export_full_tafsili_csv(request):
    """خروجی CSV کامل با تمام فیلدها (تعداد طبقات، سطح اشغال، توضیحات، مختصات)"""

    if not (request.user.groups.filter(name='expert').exists() or request.user.is_staff):
        return redirect('core_admin:login')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="tafsili_jame_complete.csv"'

    writer = csv.writer(response)

    # هدرهای جدید با فیلدهای مورد نیاز
    writer.writerow([
        'شناسه', 'عنوان پروژه', 'اپراتور', 'وضعیت', 'تاریخ ثبت', 'تاریخ تأیید',
        'کد منطقه', 'نام محله', 'کاربری تفصیلی',
        'نام معبر', 'عرض معبر (متر)', 'نوع مالکیت',
        'مساحت عرصه (متر مربع)', 'مساحت اعیانی (متر مربع)',
        'تعداد طبقات', 'سطح اشغال (%)', 'تراکم ساختمانی',
        'حداکثر طبقات', 'قدمت بنا', 'نوع نما',
        'مصالح ساختمانی', 'کیفیت ابنیه', 'سطح عملکردی',
        'کاربری طبقات بالای همکف', 'کاربری همکف', 'انواع کاربری (غالب)',
        'توضیحات',
        'عرض جغرافیایی', 'طول جغرافیایی'
    ])

    from .models import FinalTafsiliData, TafsiliPlanData
    from django.db import connection

    # استفاده از کوئری مستقیم برای اطمینان از گرفتن همه داده‌ها
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                f.id,
                p.title,
                u.username,
                f.created_at,
                f.zone_code,
                f.neighborhood,
                f.detailed_use,
                f.street_name,
                f.street_width,
                f.ownership_type,
                f.land_area,
                f.built_area,
                COALESCE(f.floor_count, t.floor_count) as floor_count,
                COALESCE(f.occupancy_rate, t.occupancy_rate) as occupancy_rate,
                f.density,
                f.floor_limit,
                f.building_age,
                f.facade_type,
                f.material_type,
                f.building_quality,
                f.functional_level,
                f.upper_floor_use,
                f.ground_floor_use,
                f.dominant_use,
                COALESCE(f.description, p.description) as description,
                COALESCE(f.latitude, ST_Y(t.location)) as latitude,
                COALESCE(f.longitude, ST_X(t.location)) as longitude
            FROM core_admin_finaltafsilidata f
            INNER JOIN core_admin_projectplan p ON f.plan_id = p.id
            INNER JOIN auth_user u ON p.operator_id = u.id
            LEFT JOIN core_admin_tafsiliplandata t ON t.plan_id = p.id
            WHERE p.status = 'approved' AND p.plan_type = 'tafsili'
            ORDER BY f.created_at DESC
        """)

        rows = cursor.fetchall()

        for row in rows:
            writer.writerow([
                str(row[0])[:8] if row[0] else '',
                row[1] or '',  # عنوان پروژه
                row[2] or '',  # اپراتور
                'تأیید شده',
                row[3].strftime('%Y/%m/%d %H:%M') if row[3] else '',  # تاریخ ثبت
                row[3].strftime('%Y/%m/%d %H:%M') if row[3] else '',  # تاریخ تأیید (همون تاریخ ثبت final)
                row[4] or '',  # کد منطقه
                row[5] or '',  # نام محله
                row[6] or '',  # کاربری تفصیلی
                row[7] or '',  # نام معبر
                row[8] or '',  # عرض معبر
                row[9] or '',  # نوع مالکیت
                row[10] or '',  # مساحت عرصه
                row[11] or '',  # مساحت اعیانی
                row[12] or '',  # تعداد طبقات
                f"{row[13]:.2f}" if row[13] else '',  # سطح اشغال
                row[14] or '',  # تراکم
                row[15] or '',  # حداکثر طبقات
                row[16] or '',  # قدمت بنا
                row[17] or '',  # نوع نما
                row[18] or '',  # مصالح
                row[19] or '',  # کیفیت ابنیه
                row[20] or '',  # سطح عملکردی
                row[21] or '',  # کاربری طبقات بالا
                row[22] or '',  # کاربری همکف
                row[23] or '',  # کاربری غالب
                row[24] or '',  # توضیحات
                f"{row[25]:.6f}" if row[25] else '',  # عرض جغرافیایی
                f"{row[26]:.6f}" if row[26] else '',  # طول جغرافیایی
            ])

    return response


@login_required
def operator_profile_view(request):
    """پروفایل مخصوص اپراتور با قابلیت آپلود عکس"""
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    # پردازش آپلود عکس (AJAX)
    if request.method == 'POST' and request.FILES.get('avatar'):
        try:
            if profile.avatar:
                profile.avatar.delete()
            profile.avatar = request.FILES['avatar']
            profile.save()
            return JsonResponse({'success': True, 'url': profile.avatar.url})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # پردازش فرم عادی
    if request.method == 'POST':
        if 'change_password' in request.POST:
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if request.user.check_password(old_password):
                if new_password1 == new_password2 and len(new_password1) >= 6:
                    request.user.set_password(new_password1)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "رمز عبور با موفقیت تغییر کرد")
                else:
                    messages.error(request, "رمز جدید معتبر نیست یا مطابقت ندارد")
            else:
                messages.error(request, "رمز عبور فعلی اشتباه است")
        else:
            request.user.first_name = request.POST.get('first_name', '')
            request.user.last_name = request.POST.get('last_name', '')
            request.user.email = request.POST.get('email', '')
            request.user.save()

            profile.phone = request.POST.get('phone', '')
            profile.bio = request.POST.get('bio', '')
            profile.save()
            messages.success(request, "اطلاعات پروفایل با موفقیت بروزرسانی شد")

        return redirect('core_admin:operator_profile')

    context = {
        'user': request.user,
        'profile': profile,
    }
    return render(request, 'core_admin/operator_profile.html', context)


@csrf_exempt
@login_required
def operator_upload_avatar(request):
    """API جداگانه برای آپلود عکس پروفایل اپراتور"""
    if not request.user.groups.filter(name='operator').exists():
        return JsonResponse({'success': False, 'error': 'دسترسی غیرمجاز'})

    if request.method == 'POST' and request.FILES.get('avatar'):
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)

            if profile.avatar:
                profile.avatar.delete()

            profile.avatar = request.FILES['avatar']
            profile.save()

            return JsonResponse({
                'success': True,
                'url': profile.avatar.url,
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'})

@csrf_exempt
@login_required
def expert_upload_avatar(request):
    """API جداگانه برای آپلود عکس پروفایل کارشناس"""
    if not request.user.groups.filter(name='expert').exists():
        return JsonResponse({'success': False, 'error': 'دسترسی غیرمجاز'})

    if request.method == 'POST' and request.FILES.get('avatar'):
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)

            if profile.avatar:
                profile.avatar.delete()

            profile.avatar = request.FILES['avatar']
            profile.save()

            return JsonResponse({
                'success': True,
                'url': profile.avatar.url,
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'})

def some_expert_view(request):
    context = {
        'user': request.user,
        'user_profile': UserProfile.objects.get_or_create(user=request.user)[0],
    }
    return render(request, 'core_admin/some_page.html', context)


@login_required
def operator_edit_plan(request, plan_id):
    """ویرایش طرح توسط اپراتور"""
    if not request.user.groups.filter(name='operator').exists():
        messages.error(request, "دسترسی غیرمجاز")
        return redirect('core_admin:operator_login')

    from .models import ProjectPlan, TafsiliPlanData
    from django.contrib.gis.geos import Point

    plan = get_object_or_404(ProjectPlan, id=plan_id, operator=request.user)

    # فقط طرح‌های در انتظار و رد شده قابل ویرایش هستند
    if plan.status not in ['pending', 'rejected']:
        messages.error(request, "این طرح قابل ویرایش نیست")
        return redirect('core_admin:operator_my_plans')

    if request.method == 'POST':
        try:
            # دریافت موقعیت مکانی
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')

            location = None
            if latitude and longitude:
                try:
                    location = Point(float(longitude), float(latitude), srid=4326)
                except:
                    pass

            # به‌روزرسانی اطلاعات طرح پایه
            plan.title = request.POST.get('title', '')
            plan.description = request.POST.get('description', '')
            plan.status = 'pending'  # برگشت به حالت در انتظار بررسی
            plan.revision_count += 1
            plan.save()

            # به‌روزرسانی اطلاعات TafsiliPlanData
            if hasattr(plan, 'tafsili_plan'):
                t = plan.tafsili_plan
                t.location = location
                t.parcel_code = request.POST.get('parcel_code', '')
                t.zone_code = request.POST.get('zone_code', '')
                t.neighborhood = request.POST.get('neighborhood', '')
                t.detailed_use = request.POST.get('detailed_use', '')
                t.street_name = request.POST.get('street_name', '')
                t.street_width = request.POST.get('street_width') or None
                t.ownership_type = request.POST.get('ownership_type', '')
                t.land_area = request.POST.get('land_area') or None
                t.built_area = request.POST.get('built_area') or None
                t.density = request.POST.get('density') or None
                t.floor_limit = request.POST.get('floor_limit') or None
                t.building_age = request.POST.get('building_age', '')
                t.facade_type = request.POST.get('facade_type', '')
                t.material_type = request.POST.get('material_type', '')
                t.building_quality = request.POST.get('building_quality', '')
                t.functional_level = request.POST.get('functional_level', '')
                t.floor_count = request.POST.get('floor_count') or None
                t.occupancy_rate = request.POST.get('occupancy_rate') or None
                t.building_status = request.POST.get('building_status', '')
                t.upper_floor_use = request.POST.get('upper_floor_use', '')
                t.ground_floor_use = request.POST.get('ground_floor_use', '')
                t.dominant_use = request.POST.get('dominant_use', '')

                if request.FILES.get('photo'):
                    t.photo = request.FILES['photo']
                t.save()

            messages.success(request, "✅ طرح با موفقیت ویرایش شد و دوباره به کارشناس ارسال گردید.")
            return redirect('core_admin:operator_my_plans')

        except Exception as e:
            messages.error(request, f"❌ خطا در ویرایش: {str(e)}")
            return redirect('core_admin:operator_edit_plan', plan_id=plan_id)

    # ==================== بخش GET ====================
    # استخراج مختصات از location
    latitude = ''
    longitude = ''

    if hasattr(plan, 'tafsili_plan') and plan.tafsili_plan and plan.tafsili_plan.location:
        latitude = plan.tafsili_plan.location.y  # عرض
        longitude = plan.tafsili_plan.location.x  # طول

    context = {
        'plan': plan,
        'tafsili': plan.tafsili_plan if hasattr(plan, 'tafsili_plan') else None,
        'latitude': latitude,
        'longitude': longitude,
    }
    return render(request, 'core_admin/operator_edit_plan.html', context)


@login_required
def export_arcgis_csv(request):
    """خروجی CSV مخصوص ArcGIS برای بروزرسانی قطعات"""

    if not (request.user.groups.filter(name='expert').exists() or request.user.is_staff):
        return redirect('core_admin:login')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="arcgis_export.csv"'

    writer = csv.writer(response)

    # هدرها - با شناسه در اولویت
    writer.writerow([
        'OBJECTID', 'عنوان پروژه', 'کد منطقه', 'نام محله', 'کاربری تفصیلی',
        'نام معبر', 'عرض معبر (متر)', 'نوع مالکیت', 'مساحت عرصه (متر مربع)',
        'مساحت اعیانی (متر مربع)', 'تعداد طبقات', 'سطح اشغال (%)', 'تراکم ساختمانی',
        'حداکثر طبقات', 'قدمت بنا', 'نوع نما', 'مصالح ساختمانی', 'کیفیت ابنیه',
        'سطح عملکردی', 'کاربری طبقات بالای همکف', 'کاربری همکف', 'انواع کاربری (غالب)',
        'توضیحات', 'عرض جغرافیایی', 'طول جغرافیایی'
    ])

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                f.id,
                p.title,
                f.zone_code,
                f.neighborhood,
                f.detailed_use,
                f.street_name,
                f.street_width,
                f.ownership_type,
                f.land_area,
                f.built_area,
                f.floor_count,
                f.occupancy_rate,
                f.density,
                f.floor_limit,
                f.building_age,
                f.facade_type,
                f.material_type,
                f.building_quality,
                f.functional_level,
                f.upper_floor_use,
                f.ground_floor_use,
                f.dominant_use,
                f.description,
                f.latitude,
                f.longitude
            FROM core_admin_finaltafsilidata f
            INNER JOIN core_admin_projectplan p ON f.plan_id = p.id
            WHERE p.status = 'approved' AND p.plan_type = 'tafsili'
            ORDER BY f.created_at DESC
        """)

        rows = cursor.fetchall()

        for row in rows:
            writer.writerow([
                row[0],  # OBJECTID - شناسه اصلی
                row[1] or '',
                row[2] or '',
                row[3] or '',
                row[4] or '',
                row[5] or '',
                row[6] or '',
                row[7] or '',
                row[8] or '',
                row[9] or '',
                row[10] or '',
                f"{row[11]:.2f}" if row[11] else '',
                row[12] or '',
                row[13] or '',
                row[14] or '',
                row[15] or '',
                row[16] or '',
                row[17] or '',
                row[18] or '',
                row[19] or '',
                row[20] or '',
                row[21] or '',
                row[22] or '',
                f"{row[23]:.6f}" if row[23] else '',
                f"{row[24]:.6f}" if row[24] else '',
            ])

    return response