from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
import re


class AdminLoginForm(forms.Form):
    """فرم لاگین ادمین"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام کاربری خود را وارد کنید',
            'autofocus': True
        }),
        label="نام کاربری"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز عبور خود را وارد کنید'
        }),
        label="رمز عبور"
    )


class UserEditForm(forms.ModelForm):
    """فرم ویرایش کاربر"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام خانوادگی'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام کاربری'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@domain.com'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
            raise ValidationError('این نام کاربری قبلاً ثبت شده است.')
        return username


class CustomUserCreationForm(UserCreationForm):
    """فرم ایجاد کاربر جدید"""
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام خانوادگی'})
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام کاربری'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'تکرار رمز عبور'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('این نام کاربری قبلاً ثبت شده است.')
        return username

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("رمز عبور و تکرار آن مطابقت ندارند.")
        if len(password1) < 6:
            raise ValidationError("رمز عبور باید حداقل ۶ کاراکتر باشد.")
        return password2


class CustomPasswordChangeForm(PasswordChangeForm):
    """فرم تغییر رمز عبور"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class BulkActionForm(forms.Form):
    """فرم عملیات گروهی"""
    ACTION_CHOICES = [
        ('', 'عملیات گروهی را انتخاب کنید...'),
        ('delete', '🗑 حذف کاربران'),
        ('activate', '✅ فعال کردن کاربران'),
        ('deactivate', '❌ غیرفعال کردن کاربران'),
        ('make_operator', '👨‍💼 تبدیل به اپراتور'),
        ('make_expert', '👨‍🔬 تبدیل به کارشناس'),
        ('remove_role', '🗑 حذف نقش کاربران'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'bulkAction'}),
        required=False
    )


class SettingsForm(forms.Form):
    """فرم تنظیمات سیستم"""
    ITEMS_PER_PAGE_CHOICES = [
        ('10', '۱۰ مورد در هر صفحه'),
        ('25', '۲۵ مورد در هر صفحه'),
        ('50', '۵۰ مورد در هر صفحه'),
        ('100', '۱۰۰ مورد در هر صفحه'),
    ]

    THEME_CHOICES = [
        ('light', 'روشن (Light)'),
        ('dark', 'تاریک (Dark)'),
        ('auto', 'خودکار (Auto)'),
    ]

    items_per_page = forms.ChoiceField(
        choices=ITEMS_PER_PAGE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="تعداد آیتم در هر صفحه",
        required=False
    )

    theme = forms.ChoiceField(
        choices=THEME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="تم سیستم",
        required=False
    )

    email_notifications = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="دریافت ایمیل‌های اطلاع‌رسانی",
        required=False
    )

    log_retention_days = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '7', 'max': '365'}),
        label="مدت نگهداری لاگ‌ها (روز)",
        required=False,
        initial=30
    )