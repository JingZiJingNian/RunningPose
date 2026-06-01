# users/pipeline.py
from .models import UserProfile


def update_user_profile(backend, user, response, *args, **kwargs):
    """更新用户资料"""
    if backend.name == 'qq':
        # 处理QQ登录
        profile, created = UserProfile.objects.get_or_create(user=user)
        if not profile.qq_openid:
            profile.qq_openid = response.get('openid', '')
            profile.save()

    elif backend.name == 'weibo':
        # 处理微博登录
        profile, created = UserProfile.objects.get_or_create(user=user)
        if not profile.weibo_uid:
            profile.weibo_uid = response.get('uid', '')
            profile.save()

    elif backend.name == 'weixin':
        # 处理微信登录
        profile, created = UserProfile.objects.get_or_create(user=user)
        if not profile.wechat_openid:
            profile.wechat_openid = response.get('openid', '')
            profile.save()