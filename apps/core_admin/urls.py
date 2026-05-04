from django.urls import path
from . import admin_views

app_name = "core_admin"

urlpatterns = [

    # ===================== احراز هویت =====================
    path("login/", admin_views.admin_login, name="login"),
    path("logout/", admin_views.admin_logout, name="logout"),
    path("login/operator/", admin_views.operator_login, name="operator_login"),
    path("login/expert/", admin_views.expert_login, name="expert_login"),

    # ===================== داشبورد =====================
    path("", admin_views.dashboard, name="dashboard"),
    path("operator/", admin_views.operator_home, name="operator_home"),
    path("expert/", admin_views.expert_dashboard, name="expert_dashboard"),

    # ===================== پروفایل و آپلود عکس =====================
    path("profile/", admin_views.profile, name="profile"),
    path("operator/profile/", admin_views.operator_profile_view, name="operator_profile"),
    path("operator/upload-avatar/", admin_views.operator_upload_avatar, name="operator_upload_avatar"),
    path("expert/profile/", admin_views.expert_profile_view, name="expert_profile"),
    path("expert/upload-avatar/", admin_views.expert_upload_avatar, name="expert_upload_avatar"),

    # ===================== تغییر رمز =====================
    path('operator/change-password/', admin_views.operator_change_password, name='operator_change_password'),

    # ===================== جریان کاری اپراتور =====================
    path('operator/select-plan/', admin_views.operator_select_plan, name='operator_select_plan'),
    path('operator/submit-tafsili/', admin_views.operator_submit_tafsili, name='operator_submit_tafsili'),
    path('operator/submit-momayezi/', admin_views.operator_submit_momayezi, name='operator_submit_momayezi'),
    path('operator/my-plans/', admin_views.operator_my_plans, name='operator_my_plans'),
    path('operator/revise-plan/<uuid:plan_id>/', admin_views.operator_revise_plan, name='operator_revise_plan'),

    # ===================== کارشناس — لیست‌ها =====================
    path('expert/tafsili-list/', admin_views.expert_tafsili_list, name='expert_tafsili_list'),
    path('expert/momayezi-list/', admin_views.expert_momayezi_list, name='expert_momayezi_list'),

    # ===================== جریان کاری کارشناس =====================
    path('expert/pending-plans/', admin_views.expert_pending_plans, name='expert_pending_plans'),
    path('expert/review-plan/<uuid:plan_id>/', admin_views.expert_review_plan, name='expert_review_plan'),
    path('expert/revised-plans/', admin_views.expert_revised_plans, name='expert_revised_plans'),
    path('expert/approved-plans/', admin_views.expert_approved_plans, name='expert_approved_plans'),

    # ===================== API های کارشناس =====================
    path('expert/stats/', admin_views.expert_stats_dashboard, name='expert_stats'),
    path('expert/plan-detail/<uuid:plan_id>/', admin_views.expert_plan_detail_api, name='expert_plan_detail_api'),
    path('expert/update-plan-status/<uuid:plan_id>/', admin_views.expert_update_plan_status, name='expert_update_plan_status'),

    # ===================== مدیریت کاربران =====================
    path("add-operator/", admin_views.add_operator, name="add_operator"),
    path("add-expert/", admin_views.add_expert, name="add_expert"),
    path("edit-user/<int:user_id>/", admin_views.edit_user, name="edit_user"),
    path("delete-user/<int:user_id>/", admin_views.delete_user, name="delete_user"),
    path("toggle-status/<int:user_id>/", admin_views.toggle_user_status, name="toggle_status"),
    path("change-role/<int:user_id>/<str:role>/", admin_views.change_role, name="change_role"),

    # ===================== عملیات گروهی =====================
    path("bulk-action/", admin_views.bulk_action, name="bulk_action"),

    # ===================== API ها =====================
    path("api/search/", admin_views.search_users_api, name="search_api"),
    path('check-session/', admin_views.check_session, name='check_session'),
    path('check-user-role/', admin_views.check_user_role, name='check_user_role'),
    path('check-role/', admin_views.check_role_redirect, name='check_role'),

    # ===================== خروجی CSV =====================
    path('export-csv/', admin_views.export_users_csv, name='export_csv'),
    path('export-final-csv/', admin_views.export_final_csv, name='export_final_csv'),
    path('export-final-detailed-csv/', admin_views.export_final_detailed_csv, name='export_final_detailed_csv'),
    path('export-full-tafsili-csv/', admin_views.export_full_tafsili_csv, name='export_full_tafsili_csv'),

    # ===================== خروج =====================
    path('logout/', admin_views.admin_logout, name='logout'),
    path("settings/", admin_views.settings_view, name="settings"),
]