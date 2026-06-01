from django.contrib.auth.models import User
from rest_framework import serializers

from .models import UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError('邮箱已被使用')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': '两次输入的密码不一致'
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    avatar_url = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    bmi = serializers.SerializerMethodField()
    bmi_category = serializers.SerializerMethodField()
    gender_display = serializers.SerializerMethodField()
    running_experience_display = serializers.SerializerMethodField()
    completion_score = serializers.SerializerMethodField()
    completion_text = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'username',
            'email',
            'avatar',
            'avatar_url',
            'bio',
            'gender',
            'gender_display',
            'birth_date',
            'height',
            'weight',
            'running_experience',
            'running_experience_display',
            'favorite_distance',
            'email_verified',
            'phone_verified',
            'age',
            'bmi',
            'bmi_category',
            'completion_score',
            'completion_text',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'email_verified',
            'phone_verified',
            'age',
            'bmi',
            'bmi_category',
            'gender_display',
            'running_experience_display',
            'completion_score',
            'completion_text',
            'created_at',
            'updated_at',
        ]

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        url = obj.get_avatar_url()
        if request and url and url.startswith('/'):
            return request.build_absolute_uri(url)
        return url

    def get_age(self, obj):
        return obj.calculate_age()

    def get_bmi(self, obj):
        return obj.calculate_bmi()

    def get_bmi_category(self, obj):
        return obj.get_bmi_category_display()

    def get_gender_display(self, obj):
        return obj.get_gender_display() if obj.gender else None

    def get_running_experience_display(self, obj):
        return obj.get_running_experience_display() if obj.running_experience else None

    def get_completion_score(self, obj):
        fields = [
            obj.avatar,
            obj.bio,
            obj.gender,
            obj.birth_date,
            obj.height,
            obj.weight,
            obj.running_experience,
            obj.favorite_distance,
            obj.user.email,
        ]
        filled = sum(1 for item in fields if item not in (None, '', False))
        return int(round(filled / len(fields) * 100))

    def get_completion_text(self, obj):
        score = self.get_completion_score(obj)
        if score >= 85:
            return '资料已较完整'
        if score >= 60:
            return '资料还可以继续完善'
        return '完善资料有助于获得更个性化的分析体验'
