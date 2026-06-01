# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import UserProfile
from datetime import date


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='邮箱')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('该邮箱已被注册')
        return email


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='用户名或邮箱',
        widget=forms.TextInput(attrs={'autofocus': True})
    )


class UserProfileForm(forms.ModelForm):
    birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='出生日期'
    )

    class Meta:
        model = UserProfile
        fields = [
            'avatar', 'bio', 'gender', 'birth_date',
            'height', 'weight', 'running_experience', 'favorite_distance'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'height': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'weight': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
        }
        labels = {
            'height': '身高 (cm)',
            'weight': '体重 (kg)',
        }
        help_texts = {
            'height': '请输入您的身高（厘米）',
            'weight': '请输入您的体重（千克）',
        }


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, label='邮箱')

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class PasswordChangeCustomForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})