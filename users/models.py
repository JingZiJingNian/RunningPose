from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
import os
from datetime import date


def validate_avatar_size(value):
    filesize = value.size
    if filesize > 4 * 1024 * 1024:
        raise ValidationError("头像文件大小不能超过 4MB")
    return value


def avatar_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f'avatar_{instance.user.id}_{instance.user.username}.{ext}'
    return os.path.join('avatars', filename)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')

    avatar = models.ImageField(
        upload_to=avatar_upload_path,
        blank=True,
        null=True,
        validators=[validate_avatar_size],
        verbose_name='头像'
    )
    bio = models.TextField(max_length=500, blank=True, verbose_name='个人简介')

    GENDER_CHOICES = [
        ('male', '男'),
        ('female', '女'),
        ('other', '其他'),
        ('prefer_not_to_say', '不愿透露'),
    ]

    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        blank=True,
        verbose_name='性别'
    )

    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='出生日期'
    )

    height = models.FloatField(
        null=True,
        blank=True,
        verbose_name='身高(cm)',
        help_text='单位：厘米'
    )

    weight = models.FloatField(
        null=True,
        blank=True,
        verbose_name='体重(kg)',
        help_text='单位：千克'
    )

    RUNNING_EXPERIENCE_CHOICES = [
        ('beginner', '初级跑者 (0-1年)'),
        ('intermediate', '中级跑者 (1-3年)'),
        ('advanced', '高级跑者 (3年以上)'),
        ('professional', '专业运动员'),
    ]

    running_experience = models.CharField(
        max_length=20,
        choices=RUNNING_EXPERIENCE_CHOICES,
        default='beginner',
        verbose_name='跑步经验'
    )

    favorite_distance = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='偏好距离',
        help_text='例如：5公里、半马、全马'
    )

    qq_openid = models.CharField(max_length=100, blank=True, verbose_name='QQ OpenID')
    wechat_openid = models.CharField(max_length=100, blank=True, verbose_name='微信 OpenID')
    weibo_uid = models.CharField(max_length=100, blank=True, verbose_name='微博 UID')

    email_verified = models.BooleanField(default=False, verbose_name='邮箱已验证')
    phone_verified = models.BooleanField(default=False, verbose_name='手机已验证')
    last_password_change = models.DateTimeField(default=timezone.now, verbose_name='最后密码修改时间')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'

    def __str__(self):
        return f"{self.user.username} 的个人资料"

    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return None

    def calculate_age(self):
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None

    def calculate_bmi(self):
        if self.height and self.weight:
            height_m = self.height / 100
            bmi = self.weight / (height_m * height_m)
            return round(bmi, 1)
        return None

    def get_bmi_category(self):
        bmi = self.calculate_bmi()
        if bmi is None:
            return None

        if bmi < 18.5:
            return 'underweight'
        if bmi < 24:
            return 'normal'
        if bmi < 28:
            return 'overweight'
        return 'obese'

    def get_bmi_category_display(self):
        category = self.get_bmi_category()
        category_map = {
            'underweight': '偏瘦',
            'normal': '正常',
            'overweight': '超重',
            'obese': '肥胖'
        }
        return category_map.get(category, '')


class LoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    ip_address = models.GenericIPAddressField(verbose_name='IP地址')
    user_agent = models.TextField(verbose_name='用户代理')
    login_time = models.DateTimeField(auto_now_add=True, verbose_name='登录时间')
    login_type = models.CharField(
        max_length=20,
        choices=[
            ('password', '密码登录'),
            ('qq', 'QQ登录'),
            ('wechat', '微信登录'),
            ('weibo', '微博登录'),
        ],
        default='password',
        verbose_name='登录方式'
    )

    class Meta:
        verbose_name = '登录历史'
        verbose_name_plural = '登录历史'
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()
