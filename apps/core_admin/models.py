from django.db import models
from django.contrib.auth.models import User
from django.contrib.gis.db import models as gis_models
import uuid


class Project(models.Model):
    """پروژه نقشه‌برداری"""
    name = models.CharField(max_length=200, verbose_name="نام پروژه")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "پروژه"
        verbose_name_plural = "پروژه‌ها"


class Feature(models.Model):
    """قطعه/عارضه مکانی"""
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('submitted', 'ثبت شده'),
        ('approved', 'تأیید شده'),
        ('rejected', 'رد شده'),
    ]

    feature_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='features')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='features')

    # اطلاعات مکانی با PostGIS
    location = gis_models.PointField(srid=4326, verbose_name="موقعیت مکانی", null=True, blank=True)

    # اطلاعات توصیفی
    land_use = models.CharField(max_length=100, blank=True, verbose_name="کاربری اراضی")
    area_sqm = models.FloatField(null=True, blank=True, verbose_name="مساحت (متر مربع)")
    owner_name = models.CharField(max_length=200, blank=True, verbose_name="نام مالک")
    address = models.TextField(blank=True, verbose_name="آدرس")
    description = models.TextField(blank=True, verbose_name="توضیحات")

    # وضعیت
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')

    # زمان
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # عکس
    photo = models.ImageField(upload_to='features/', blank=True, null=True)

    # نظر کارشناس
    review_note = models.TextField(blank=True, verbose_name="نظر کارشناس")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='reviewed_features')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.feature_id} - {self.project.name}"

    class Meta:
        verbose_name = "قطعه"
        verbose_name_plural = "قطعات"
        ordering = ['-recorded_at']


class FeatureAttachment(models.Model):
    """فایل‌های ضمیمه قطعه (عکس‌های بیشتر)"""
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='feature_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.feature.feature_id} - {self.uploaded_at}"

    class Meta:
        verbose_name = "ضمیمه قطعه"
        verbose_name_plural = "ضمیمه‌های قطعه"


# ========== مدل‌های پروفایل اپراتور ==========
class OperatorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='operator_profile')
    national_id = models.CharField(max_length=10, blank=True, verbose_name="شماره شناسنامه")
    personal_code = models.CharField(max_length=20, blank=True, verbose_name="شماره پرسنلی")
    phone = models.CharField(max_length=11, blank=True, verbose_name="شماره موبایل")
    email = models.EmailField(blank=True, verbose_name="ایمیل")
    profile_picture = models.ImageField(upload_to='operator_profiles/', blank=True, null=True,
                                        verbose_name="عکس پروفایل")
    address = models.TextField(blank=True, verbose_name="آدرس")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"پروفایل {self.user.username}"

    class Meta:
        verbose_name = "پروفایل اپراتور"
        verbose_name_plural = "پروفایل اپراتورها"


# ========== مدل‌های جریان کاری طرح‌ها ==========

class ProjectPlan(models.Model):
    """مدل اصلی برای طرح‌های اپراتور (با گردش کار)"""
    PLAN_TYPES = [
        ('tafsili', 'طرح تفصیلی / جامع'),
        ('momayezi', 'ممیزی املاک'),
    ]

    STATUS_CHOICES = [
        ('pending', 'در انتظار بررسی'),
        ('approved', 'تأیید شده'),
        ('rejected', 'رد شده'),
        ('revised', 'نیاز به اصلاح'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, verbose_name="نوع طرح")
    operator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_plans', verbose_name="اپراتور")
    expert = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_plans',
                               verbose_name="کارشناس")

    # اطلاعات مشترک
    title = models.CharField(max_length=200, verbose_name="عنوان پروژه")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # وضعیت
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expert_note = models.TextField(blank=True, verbose_name="نظر کارشناس")
    revision_count = models.IntegerField(default=0, verbose_name="تعداد دفعات اصلاح")

    # اطلاعات نهایی (بعد از تأیید کارشناس)
    is_final = models.BooleanField(default=False, verbose_name="ثبت نهایی در دیتابیس")
    final_data = models.JSONField(default=dict, blank=True, verbose_name="داده‌های نهایی")

    def __str__(self):
        return f"{self.get_plan_type_display()} - {self.title} - {self.get_status_display()}"

    class Meta:
        verbose_name = "طرح پروژه"
        verbose_name_plural = "طرح‌های پروژه"
        ordering = ['-created_at']


class TafsiliPlanData(models.Model):
    plan = models.OneToOneField(ProjectPlan, on_delete=models.CASCADE, related_name='tafsili_plan')

    # 📋 اطلاعات پایه
    zone_code = models.CharField('کد منطقه', max_length=50, blank=True)
    land_use_type = models.CharField('نوع کاربری اراضی', max_length=100, blank=True)
    neighborhood = models.CharField('نام محله', max_length=100, blank=True)
    detailed_use = models.TextField('کاربری تفصیلی', blank=True)

    # 🏙️ اطلاعات شهری
    street_name = models.CharField('نام معبر', max_length=200, blank=True)
    street_width = models.FloatField('عرض معبر (متر)', null=True, blank=True)
    ownership_type = models.CharField('نوع مالکیت', max_length=50, blank=True)
    land_area = models.FloatField('مساحت عرصه (متر مربع)', null=True, blank=True)

    # 🏗️ اطلاعات ساختمانی
    density = models.FloatField('تراکم ساختمانی', null=True, blank=True)
    floor_limit = models.IntegerField('حداکثر طبقات', null=True, blank=True)
    built_area = models.FloatField('مساحت اعیانی (متر مربع)', null=True, blank=True)
    building_age = models.CharField('قدمت بنا', max_length=50, blank=True)
    facade_type = models.CharField('نوع نما', max_length=100, blank=True)
    material_type = models.CharField('مصالح ساختمانی', max_length=100, blank=True)
    building_quality = models.CharField('کیفیت ابنیه', max_length=50, blank=True)
    functional_level = models.CharField('سطح عملکردی', max_length=100, blank=True)
    parcel_code = models.CharField('کد پلاک', max_length=50, blank=True)

    # 🏪 اطلاعات کاربری
    upper_floor_use = models.CharField('کاربری طبقات بالای همکف', max_length=100, blank=True)
    ground_floor_use = models.CharField('کاربری همکف', max_length=100, blank=True)
    dominant_use = models.CharField('انواع کاربری (غالب)', max_length=100, blank=True)

    photo = models.ImageField('عکس', upload_to='tafsili_plans/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"طرح تفصیلی - {self.plan.title}"


class FinalTafsiliData(models.Model):
    plan = models.OneToOneField(ProjectPlan, on_delete=models.CASCADE, related_name='final_tafsili')

    # 📋 اطلاعات پایه
    zone_code = models.CharField('کد منطقه', max_length=50)
    land_use_type = models.CharField('نوع کاربری اراضی', max_length=100)
    neighborhood = models.CharField('نام محله', max_length=100, blank=True)
    detailed_use = models.TextField('کاربری تفصیلی', blank=True)

    # 🏙️ اطلاعات شهری
    street_name = models.CharField('نام معبر', max_length=200)
    street_width = models.FloatField('عرض معبر (متر)', null=True, blank=True)
    ownership_type = models.CharField('نوع مالکیت', max_length=50)
    land_area = models.FloatField('مساحت عرصه (متر مربع)', null=True, blank=True)

    # 🏗️ اطلاعات ساختمانی
    density = models.FloatField('تراکم ساختمانی', null=True, blank=True)
    floor_limit = models.IntegerField('حداکثر طبقات', null=True, blank=True)
    built_area = models.FloatField('مساحت اعیانی (متر مربع)', null=True, blank=True)
    building_age = models.CharField('قدمت بنا', max_length=50, blank=True)
    facade_type = models.CharField('نوع نما', max_length=100, blank=True)
    material_type = models.CharField('مصالح ساختمانی', max_length=100, blank=True)
    building_quality = models.CharField('کیفیت ابنیه', max_length=50, blank=True)
    functional_level = models.CharField('سطح عملکردی', max_length=100, blank=True)
    parcel_code = models.CharField('کد پلاک', max_length=50, blank=True)

    # 🏪 اطلاعات کاربری
    upper_floor_use = models.CharField('کاربری طبقات بالای همکف', max_length=100, blank=True)
    ground_floor_use = models.CharField('کاربری همکف', max_length=100, blank=True)
    dominant_use = models.CharField('انواع کاربری (غالب)', max_length=100, blank=True)

    photo = models.ImageField('عکس', upload_to='final_tafsili/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"نهایی - {self.plan.title}"


class MomayeziPlanData(models.Model):
    """داده‌های ممیزی املاک (مرتبط با گردش کار)"""
    OWNERSHIP_CHOICES = [
        ('private', 'خصوصی'),
        ('public', 'دولتی'),
        ('endowment', 'وقف'),
        ('joint', 'مشاع'),
    ]

    BUILDING_TYPE_CHOICES = [
        ('residential', 'مسکونی'),
        ('commercial', 'تجاری'),
        ('office', 'اداری'),
        ('industrial', 'صنعتی'),
        ('mixed', 'مختلط'),
    ]

    plan = models.OneToOneField(ProjectPlan, on_delete=models.CASCADE, related_name='momayezi_plan')
    parcel_code = models.CharField(max_length=50, verbose_name="کد پلاک")
    ownership_type = models.CharField(max_length=50, choices=OWNERSHIP_CHOICES, verbose_name="نوع مالکیت")
    owner_name = models.CharField(max_length=200, verbose_name="نام مالک")
    building_type = models.CharField(max_length=50, choices=BUILDING_TYPE_CHOICES, verbose_name="نوع بنا")
    area = models.FloatField(verbose_name="مساحت (متر مربع)")
    construction_year = models.IntegerField(verbose_name="سال ساخت")
    is_licensed = models.BooleanField(default=False, verbose_name="دارای پروانه ساخت")
    attachment = models.FileField(upload_to='momayezi_plans/', blank=True, null=True, verbose_name="فایل پیوست")

    def __str__(self):
        return f"ممیزی املاک - {self.plan.title}"


class PlanRevisionHistory(models.Model):
    """تاریخچه اصلاحات طرح‌ها"""
    plan = models.ForeignKey(ProjectPlan, on_delete=models.CASCADE, related_name='revisions')
    revision_number = models.IntegerField(verbose_name="شماره اصلاح")
    operator_data = models.JSONField(default=dict, verbose_name="داده‌های ارسالی اپراتور")
    expert_note = models.TextField(verbose_name="نظر کارشناس")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"اصلاح {self.revision_number} - {self.plan.title}"

    class Meta:
        verbose_name = "تاریخچه اصلاح طرح"
        verbose_name_plural = "تاریخچه اصلاحات طرح‌ها"
        ordering = ['-created_at']


# ========== مدل‌های نهایی (ذخیره پس از تأیید کارشناس) ==========

# ========== مدل‌های نهایی (برای داده‌های تأیید شده) ==========

class FinalTafsiliData(models.Model):
    plan = models.OneToOneField(ProjectPlan, on_delete=models.CASCADE, related_name='final_tafsili')

    # 📋 اطلاعات پایه
    zone_code = models.CharField('کد منطقه', max_length=50)
    land_use_type = models.CharField('نوع کاربری اراضی', max_length=100)
    neighborhood = models.CharField('نام محله', max_length=100, blank=True)
    detailed_use = models.TextField('کاربری تفصیلی', blank=True)

    # 🏙️ اطلاعات شهری
    street_name = models.CharField('نام معبر', max_length=200)
    street_width = models.FloatField('عرض معبر (متر)', null=True, blank=True)
    ownership_type = models.CharField('نوع مالکیت', max_length=50)
    land_area = models.FloatField('مساحت عرصه (متر مربع)', null=True, blank=True)

    # 🏗️ اطلاعات ساختمانی
    density = models.FloatField('تراکم ساختمانی', null=True, blank=True)
    floor_limit = models.IntegerField('حداکثر طبقات', null=True, blank=True)
    built_area = models.FloatField('مساحت اعیانی (متر مربع)', null=True, blank=True)
    building_age = models.CharField('قدمت بنا', max_length=50, blank=True)
    facade_type = models.CharField('نوع نما', max_length=100, blank=True)
    material_type = models.CharField('مصالح ساختمانی', max_length=100, blank=True)
    building_quality = models.CharField('کیفیت ابنیه', max_length=50, blank=True)
    functional_level = models.CharField('سطح عملکردی', max_length=100, blank=True)
    parcel_code = models.CharField('کد پلاک', max_length=50, blank=True)

    # 🏪 اطلاعات کاربری
    upper_floor_use = models.CharField('کاربری طبقات بالای همکف', max_length=100, blank=True)
    ground_floor_use = models.CharField('کاربری همکف', max_length=100, blank=True)
    dominant_use = models.CharField('انواع کاربری (غالب)', max_length=100, blank=True)

    photo = models.ImageField('عکس', upload_to='final_tafsili/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"نهایی - {self.plan.title}"

class FinalJameData(models.Model):
    """داده‌های نهایی طرح جامع - فقط پس از تأیید کارشناس"""
    plan = models.OneToOneField(ProjectPlan, on_delete=models.CASCADE, related_name='final_jame')

    zone_type = models.CharField(max_length=50, blank=True, null=True)
    green_percent = models.FloatField(blank=True, null=True)
    service_centers = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "داده نهایی طرح جامع"
        verbose_name_plural = "داده‌های نهایی طرح جامع"


class FinalMomayeziData(models.Model):
    """داده‌های نهایی ممیزی املاک - فقط پس از تأیید کارشناس"""
    plan = models.OneToOneField(ProjectPlan, on_delete=models.CASCADE, related_name='final_momayezi')

    parcel_code = models.CharField(max_length=50, blank=True, null=True)
    ownership_type = models.CharField(max_length=50, blank=True, null=True)
    owner_name = models.CharField(max_length=200, blank=True, null=True)
    building_type = models.CharField(max_length=50, blank=True, null=True)
    area = models.FloatField(blank=True, null=True)
    construction_year = models.IntegerField(blank=True, null=True)
    is_licensed = models.BooleanField(default=False)
    attachment = models.FileField(upload_to='final/momayezi/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "داده نهایی ممیزی املاک"
        verbose_name_plural = "داده‌های نهایی ممیزی املاک"

class FinalMomayeziData(models.Model):
    """داده‌های نهایی ممیزی املاک - پس از تأیید کارشناس"""
    plan = models.OneToOneField(ProjectPlan, on_delete=models.CASCADE, related_name='final_momayezi')
    parcel_code = models.CharField(max_length=50, verbose_name="کد پلاک")
    ownership_type = models.CharField(max_length=50, verbose_name="نوع مالکیت")
    owner_name = models.CharField(max_length=200, verbose_name="نام مالک")
    building_type = models.CharField(max_length=50, verbose_name="نوع بنا")
    area = models.FloatField(verbose_name="مساحت (متر مربع)")
    construction_year = models.IntegerField(verbose_name="سال ساخت")
    is_licensed = models.BooleanField(default=False, verbose_name="دارای پروانه ساخت")
    attachment = models.FileField(upload_to='final/momayezi/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"نهایی - {self.plan.title}"

    class Meta:
        verbose_name = "داده نهایی ممیزی املاک"
        verbose_name_plural = "داده‌های نهایی ممیزی املاک"
        ordering = ['-created_at']


# ========== مدل‌های قبلی طرح‌ها (برای سازگاری با نسخه قبل) ==========

class TafsiliPlanData(models.Model):
    plan = models.OneToOneField(ProjectPlan, on_delete=models.CASCADE, related_name='tafsili_plan')

    # اطلاعات پایه
    zone_code = models.CharField(max_length=50, blank=True, null=True)
    land_use_type = models.CharField(max_length=100, blank=True, null=True)
    detailed_use = models.TextField(blank=True, null=True)
    density = models.FloatField(blank=True, null=True)
    floor_limit = models.IntegerField(blank=True, null=True)
    photo = models.ImageField(upload_to='tafsili_plans/', blank=True, null=True)

    # اطلاعات شهری
    street_name = models.CharField(max_length=200, blank=True, null=True)
    street_width = models.FloatField(blank=True, null=True)
    ownership_type = models.CharField(max_length=50, blank=True, null=True)
    neighborhood = models.CharField(max_length=100, blank=True, null=True)

    # اطلاعات ساختمانی
    building_age = models.CharField(max_length=50, blank=True, null=True)
    facade_type = models.CharField(max_length=50, blank=True, null=True)
    material_type = models.CharField(max_length=50, blank=True, null=True)
    building_quality = models.CharField(max_length=50, blank=True, null=True)
    functional_level = models.CharField(max_length=50, blank=True, null=True)
    land_area = models.FloatField(blank=True, null=True)
    built_area = models.FloatField(blank=True, null=True)

    # اطلاعات کاربری
    upper_floor_use = models.CharField(max_length=100, blank=True, null=True)
    ground_floor_use = models.CharField(max_length=100, blank=True, null=True)
    dominant_use = models.CharField(max_length=100, blank=True, null=True)
    parcel_code = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"طرح تفصیلی - {self.plan.title}"

class JameData(models.Model):
    """داده‌های طرح جامع (قدیمی - برای سازگاری)"""
    operator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jame_data')
    project_name = models.CharField(max_length=200, verbose_name="نام پروژه")
    zone_type = models.CharField(max_length=100, verbose_name="نوع پهنه")
    green_percent = models.FloatField(verbose_name="درصد فضای سبز")
    service_centers = models.TextField(verbose_name="مراکز خدماتی نزدیک")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project_name} - {self.operator.username}"

    class Meta:
        verbose_name = "داده طرح جامع"
        verbose_name_plural = "داده‌های طرح جامع"
        ordering = ['-created_at']


class MomayeziData(models.Model):
    """داده‌های طرح موضوعی (قدیمی - برای سازگاری)"""
    operator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='momayezi_data')
    subject = models.CharField(max_length=200, verbose_name="موضوع پروژه")
    description = models.TextField(verbose_name="توضیحات تکمیلی")
    attachment = models.FileField(upload_to='momayezi_files/', blank=True, null=True, verbose_name="فایل پیوست")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.operator.username}"

    class Meta:
        verbose_name = "داده طرح موضوعی"
        verbose_name_plural = "داده‌های طرح موضوعی"
        ordering = ['-created_at']


# apps/core_admin/models.py
from django.db import models
from django.contrib.auth.models import User


# در انتهای فایل models.py اضافه کنید:

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="عکس پروفایل")
    phone = models.CharField(max_length=15, null=True, blank=True, verbose_name="تلفن همراه")
    bio = models.TextField(null=True, blank=True, verbose_name="بیوگرافی")
    address = models.TextField(null=True, blank=True, verbose_name="آدرس")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"پروفایل {self.user.username}"

    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل کاربران"