from django.contrib import admin
from django.contrib.auth.models import Group
from .models import GroupUserBackup
from django.urls import path
from django.shortcuts import render

def groups_overview_view(request):
    groups = Group.objects.all().prefetch_related("user_set")
    context = admin.site.each_context(request)
    context.update({"title": "نمای کلی گروه‌ها و اعضا", "groups": groups})
    return render(request, "users/groups_overview.html", context)

original_get_urls = admin.site.get_urls

def get_urls():
    urls = original_get_urls()
    custom_urls = [path("groups-overview/", admin.site.admin_view(groups_overview_view), name="groups-overview")]
    return custom_urls + urls

admin.site.get_urls = get_urls
admin.site.index_template = "admin/custom_index.html"

admin.site.register(GroupUserBackup)