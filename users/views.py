from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
import os

from .models import UserProfile, LoginHistory
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm,
    UserProfileForm, UserUpdateForm, PasswordChangeCustomForm
)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def register(request):
    if request.user.is_authenticated:
        return redirect('main:dashboard')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            LoginHistory.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                login_type='password'
            )

            raw_password = form.cleaned_data.get('password1')
            authenticated_user = authenticate(
                request,
                username=user.username,
                password=raw_password
            )
            if authenticated_user is not None:
                login(request, authenticated_user)

            messages.success(request, '注册成功，欢迎开始你的第一次跑姿分析。')
            return redirect('main:dashboard')

        messages.error(request, '注册失败，请检查填写的信息。')
    else:
        form = CustomUserCreationForm()

    return render(request, 'users/register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        return redirect('main:dashboard')

    next_url = request.GET.get('next') or request.POST.get('next') or 'main:dashboard'

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)

                LoginHistory.objects.create(
                    user=user,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    login_type='password'
                )

                messages.success(request, f'欢迎回来，{user.username}。')
                return redirect(next_url)

            messages.error(request, '用户名或密码错误。')
        else:
            messages.error(request, '用户名或密码错误。')
    else:
        form = CustomAuthenticationForm()

    social_auth_urls = {
        'qq': '/oauth/login/qq/',
        'weixin': '/oauth/login/weixin/',
        'weibo': '/oauth/login/weibo/',
    }

    return render(request, 'users/login.html', {
        'form': form,
        'social_auth_urls': social_auth_urls,
        'next': next_url,
    })


def user_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, '你已安全退出登录。')
        return redirect('users:logout_done')
    return render(request, 'users/logout_confirm.html')


def logout_done(request):
    return render(request, 'users/logout.html')


@login_required
def profile(request):
    user_profile = UserProfile.objects.get(user=request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, '个人资料已更新。')
            return redirect('users:profile')
        messages.error(request, '保存失败，请检查表单中的信息。')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileForm(instance=user_profile)

    bmi_info = None
    if user_profile.height and user_profile.weight:
        bmi_info = {
            'bmi': user_profile.calculate_bmi(),
            'category': user_profile.get_bmi_category_display()
        }

    age = user_profile.calculate_age()

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'bmi_info': bmi_info,
        'age': age,
        'user_profile': user_profile,
    }
    return render(request, 'users/profile.html', context)


@login_required
def security_settings(request):
    user_profile = UserProfile.objects.get(user=request.user)

    if request.method == 'POST':
        form = PasswordChangeCustomForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            user_profile.last_password_change = timezone.now()
            user_profile.save()

            messages.success(request, '密码修改成功。')
            return redirect('users:security_settings')
        messages.error(request, '密码修改失败，请检查输入内容。')
    else:
        form = PasswordChangeCustomForm(request.user)

    return render(request, 'users/security.html', {
        'form': form,
        'user_profile': user_profile,
    })


@login_required
def delete_avatar(request):
    if request.method == 'POST':
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.avatar:
            if os.path.isfile(user_profile.avatar.path):
                os.remove(user_profile.avatar.path)
            user_profile.avatar.delete()
            user_profile.save()
            messages.success(request, '头像已删除。')
        return redirect('users:profile')

    return JsonResponse({'error': '方法不允许'}, status=405)


@login_required
def login_history(request):
    history = LoginHistory.objects.filter(user=request.user).order_by('-login_time')
    return render(request, 'users/login_history.html', {
        'login_history': history,
    })