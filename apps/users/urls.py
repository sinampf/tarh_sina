from django.urls import path, include
from . import views
from django.contrib.auth.views import LogoutView

app_name = "users"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", LogoutView.as_view(next_page='/users/login/'), name="logout"),
    path("operator/", views.operator_panel, name="operator_panel"),
    path("expert/", views.expert_panel, name="expert_panel"),
    path("admin-panel/", include("apps.core_admin.urls", namespace="core_admin")),
]