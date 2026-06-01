from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import UserProfile, LoginHistory
from .serializers import RegisterSerializer, UserSerializer, UserProfileSerializer


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def first_error_text(errors):
    if isinstance(errors, dict):
        for value in errors.values():
            return first_error_text(value)
    if isinstance(errors, list) and errors:
        return first_error_text(errors[0])
    return str(errors)


def normalize_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def normalize_float(value):
    value = normalize_text(value)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        raise ValueError('请输入合法的数字')


@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)

    LoginHistory.objects.create(
        user=user,
        ip_address=get_client_ip(request) or '127.0.0.1',
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        login_type='password'
    )

    return Response({
        'token': token.key,
        'user': UserSerializer(user).data,
        'profile': UserProfileSerializer(user.userprofile, context={'request': request}).data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''

    user = authenticate(username=username, password=password)
    if user is None:
        return Response({
            'detail': '用户名或密码错误'
        }, status=status.HTTP_400_BAD_REQUEST)

    token, _ = Token.objects.get_or_create(user=user)

    LoginHistory.objects.create(
        user=user,
        ip_address=get_client_ip(request) or '127.0.0.1',
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        login_type='password'
    )

    return Response({
        'token': token.key,
        'user': UserSerializer(user).data,
        'profile': UserProfileSerializer(user.userprofile, context={'request': request}).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response({'detail': '已退出登录'})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def api_profile(request):
    profile = request.user.userprofile

    if request.method == 'GET':
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    allowed_profile_fields = {
        'avatar',
        'bio',
        'gender',
        'birth_date',
        'height',
        'weight',
        'running_experience',
        'favorite_distance',
    }

    try:
        if 'email' in request.data:
            email = normalize_text(request.data.get('email'))
            current_email = (request.user.email or '').strip()

            if email and email != current_email:
                if User.objects.exclude(id=request.user.id).filter(email=email).exists():
                    return Response(
                        {'errors': {'email': ['邮箱已被使用']}},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                request.user.email = email
                request.user.save(update_fields=['email'])

        profile_data = {}

        if 'bio' in request.data:
            profile_data['bio'] = normalize_text(request.data.get('bio')) or ''

        if 'gender' in request.data:
            gender = normalize_text(request.data.get('gender'))
            if gender:
                profile_data['gender'] = gender

        if 'birth_date' in request.data:
            birth_date = normalize_text(request.data.get('birth_date'))
            if birth_date:
                profile_data['birth_date'] = birth_date

        if 'height' in request.data:
            height = normalize_float(request.data.get('height'))
            if height is not None:
                profile_data['height'] = height

        if 'weight' in request.data:
            weight = normalize_float(request.data.get('weight'))
            if weight is not None:
                profile_data['weight'] = weight

        if 'running_experience' in request.data:
            running_experience = normalize_text(request.data.get('running_experience'))
            if running_experience:
                profile_data['running_experience'] = running_experience

        if 'favorite_distance' in request.data:
            favorite_distance = normalize_text(request.data.get('favorite_distance'))
            if favorite_distance:
                profile_data['favorite_distance'] = favorite_distance

        if 'avatar' in request.data and request.data.get('avatar'):
            profile_data['avatar'] = request.data.get('avatar')

        serializer = UserProfileSerializer(
            profile,
            data=profile_data,
            partial=True,
            context={'request': request},
        )

        if not serializer.is_valid():
            return Response(
                {
                    'errors': serializer.errors,
                    'detail': first_error_text(serializer.errors)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

        refreshed = UserProfile.objects.get(pk=profile.pk)
        return Response(UserProfileSerializer(refreshed, context={'request': request}).data)

    except ValueError as e:
        return Response(
            {'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'detail': f'资料更新异常: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
