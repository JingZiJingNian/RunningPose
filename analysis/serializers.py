from rest_framework import serializers
from .models import VideoUpload, AnalysisResult


def metric_obj(metrics, key):
    item = (metrics or {}).get(key)
    if isinstance(item, dict):
        return item
    if item is None:
        return None
    return {"value": item}


def metric_value(metrics, key, default=None):
    item = metric_obj(metrics, key)
    if not item:
        return default
    return item.get("value", default)


def metric_unit(metrics, key, default=""):
    item = metric_obj(metrics, key)
    if not item:
        return default
    return item.get("unit", default) or default


def metric_confidence(metrics, key, default=None):
    item = metric_obj(metrics, key)
    if not item:
        return default
    return item.get("confidence", default)


def format_metric_display(value, unit=""):
    if value is None:
        return "--"
    try:
        num = float(value)
        if unit:
            return f"{num:.2f} {unit}"
        return f"{num:.2f}"
    except Exception:
        return str(value)


def derive_conclusion(issues, metrics):
    issues = issues or []
    high_count = sum(1 for i in issues if (i.get("severity") or "").lower() == "high")
    medium_count = sum(1 for i in issues if (i.get("severity") or "").lower() == "medium")

    if high_count >= 1:
        level = "attention"
        title = "本次分析存在需要优先关注的问题"
        summary = "检测到较明显的动作风险信号，建议优先结合关键指标与改进建议进行针对性调整。"
    elif medium_count >= 2 or len(issues) >= 3:
        level = "improve"
        title = "本次分析识别到若干可优化点"
        summary = "整体动作基础可用，但仍存在影响效率或稳定性的细节问题，适合继续做结构化优化。"
    elif len(issues) >= 1:
        level = "good"
        title = "本次分析整体表现较稳定"
        summary = "仅识别到少量轻度问题，整体动作较为稳定，可继续围绕节奏与效率进行优化。"
    else:
        level = "excellent"
        title = "本次分析未发现显著问题"
        summary = "当前动作模式整体稳定，未识别到明显异常，可继续保持并观察长期趋势。"

    return {
        "level": level,
        "title": title,
        "summary": summary,
        "issue_count": len(issues),
    }


def derive_suggestions(issues):
    default_suggestion_map = {
        "overstride": {
            "title": "减少过度前伸落地",
            "detail": "尝试提升步频并让落地点更接近身体重心下方，减轻刹车感和前向冲击。"
        },
        "long_ground_contact": {
            "title": "缩短支撑拖沓感",
            "detail": "关注支撑转换节奏与离地反应，结合轻快步频和下肢力量练习改善触地效率。"
        },
        "excessive_trunk_lean": {
            "title": "优化躯干前倾控制",
            "detail": "避免从腰部过度折叠，保持躯干整体稳定前倾，配合核心与臀部控制训练。"
        },
        "excessive_vertical_oscillation": {
            "title": "减少无效上下起伏",
            "detail": "通过提升节奏感、减少上身多余摆动和改善支撑稳定性，降低垂直方向能量浪费。"
        },
        "low_cadence": {
            "title": "逐步提升步频",
            "detail": "在轻松跑中小幅提升步频，观察落地位置与动作轻盈度是否改善。"
        },
        "left_right_asymmetry": {
            "title": "关注左右侧对称性",
            "detail": "重点留意摆臂、支撑与离地节奏是否存在左右差异，可结合单侧力量与稳定训练。"
        },
    }

    suggestions = []
    seen = set()

    for issue in issues or []:
        issue_key = issue.get("issue") or issue.get("code") or ""
        suggestion_text = issue.get("suggestion") or issue.get("advice")
        label = issue.get("label") or issue_key or "动作优化建议"

        if suggestion_text:
            title = label
            detail = suggestion_text
        else:
            mapped = default_suggestion_map.get(issue_key)
            if not mapped:
                continue
            title = mapped["title"]
            detail = mapped["detail"]

        dedupe_key = f"{title}|{detail}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        suggestions.append({
            "title": title,
            "detail": detail,
        })

    if not suggestions:
        suggestions.append({
            "title": "保持当前节奏与稳定性",
            "detail": "当前未识别到明显异常，可继续通过常规训练维持动作稳定，并结合后续记录观察趋势变化。"
        })

    return suggestions


def normalize_landmark_dict(item):
    if not isinstance(item, dict):
        return None
    x = item.get("x")
    y = item.get("y")
    if x is None or y is None:
        return None
    return {
        "x": x,
        "y": y,
        "z": item.get("z"),
        "visibility": item.get("visibility"),
    }


def normalize_landmark_list(items):
    if not isinstance(items, list):
        return []
    normalized = []
    for item in items:
        lm = normalize_landmark_dict(item)
        if lm is not None:
            normalized.append(lm)
    return normalized


def compute_pose_sample_count(total_frames, duration_seconds):
    """
    返回更高密度的骨架采样帧数：
    - 最少 48
    - 常规 60~96
    - 最多 120
    """
    if total_frames <= 0:
        return 48

    duration_seconds = duration_seconds or 0
    # 按时长 roughly 12 fps 的采样上限，但不超过 120
    dynamic_count = int(max(48, min(120, duration_seconds * 12)))
    return min(total_frames, dynamic_count)


def sample_pose_frames(frames, max_frames=24, duration_seconds=None):
    frames = frames or []
    if not frames:
        return []

    effective_max = compute_pose_sample_count(len(frames), duration_seconds)

    n = len(frames)
    if n <= effective_max:
        indices = list(range(n))
    else:
        step = max(1, n / float(effective_max))
        indices = []
        current = 0.0
        while int(current) < n and len(indices) < effective_max:
            idx = int(current)
            if not indices or idx != indices[-1]:
                indices.append(idx)
            current += step

    sampled = []
    for i in indices:
        frame = frames[i]
        if not isinstance(frame, dict):
            continue

        landmarks_2d = normalize_landmark_list(frame.get("landmarks_2d"))
        landmarks_3d = normalize_landmark_list(frame.get("landmarks_3d"))

        sampled.append({
            "frame_index": frame.get("frame", i),
            "timestamp": frame.get("time"),
            "landmarks": landmarks_2d,
            "landmarks_2d": landmarks_2d,
            "landmarks_3d": landmarks_3d,
        })

    return sampled


def scatter_points(items):
    points = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        x = item.get("x")
        y = item.get("y") if item.get("y") is not None else item.get("value")
        if x is None or y is None:
            continue
        try:
            points.append({
                "x": float(x),
                "y": float(y),
            })
        except Exception:
            continue
    return points


def wave_points(obj):
    if not isinstance(obj, dict):
        return []
    xs = obj.get("x") or []
    ys = obj.get("y") or []
    points = []
    for x, y in zip(xs, ys):
        if x is None or y is None:
            continue
        try:
            points.append({
                "x": float(x),
                "y": float(y),
            })
        except Exception:
            continue
    return points


def build_trend_series(metrics):
    timeseries = (metrics or {}).get("timeseries") or {}

    return [
        {
            "key": "cadence",
            "label": "步频",
            "unit": "spm",
            "points": scatter_points(timeseries.get("cadence_scatter")),
        },
        {
            "key": "stride_length",
            "label": "步幅",
            "unit": "m",
            "points": scatter_points(timeseries.get("stride_length_scatter")),
        },
        {
            "key": "ground_contact_time",
            "label": "触地时间",
            "unit": "ms",
            "points": scatter_points(timeseries.get("ground_contact_time_scatter")),
        },
        {
            "key": "flight_time",
            "label": "腾空时间",
            "unit": "ms",
            "points": scatter_points(timeseries.get("flight_time_scatter")),
        },
        {
            "key": "trunk_lean_angle",
            "label": "躯干前倾角",
            "unit": "deg",
            "points": wave_points(timeseries.get("trunk_lean_angle_wave")),
        },
        {
            "key": "vertical_oscillation_rel",
            "label": "垂直振幅",
            "unit": "",
            "points": wave_points(timeseries.get("vertical_oscillation_wave")),
        },
    ]


class VideoUploadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoUpload
        fields = ['title', 'video_file', 'start_time', 'end_time']

    def validate(self, attrs):
        start_time = attrs.get('start_time', 0) or 0
        end_time = attrs.get('end_time')

        if start_time < 0:
            raise serializers.ValidationError({'start_time': '开始时间不能为负数'})

        if end_time is not None:
            if end_time <= start_time:
                raise serializers.ValidationError({'end_time': '结束时间必须大于开始时间'})
            if (end_time - start_time) < 5:
                raise serializers.ValidationError({'end_time': '分析片段至少需要 5 秒'})

        return attrs

    def validate_video_file(self, value):
        allowed_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        file_ext = None
        if value and value.name:
            import os
            file_ext = os.path.splitext(value.name)[1].lower()

        if file_ext not in allowed_extensions:
            raise serializers.ValidationError('只支持 MP4、MOV、AVI、MKV、WEBM 格式')

        if value.size > 100 * 1024 * 1024:
            raise serializers.ValidationError('文件大小不能超过 100MB')

        return value


class VideoUploadStatusSerializer(serializers.ModelSerializer):
    has_result = serializers.SerializerMethodField()

    class Meta:
        model = VideoUpload
        fields = [
            'id',
            'title',
            'status',
            'progress',
            'progress_message',
            'error_message',
            'uploaded_at',
            'start_time',
            'end_time',
            'has_result',
        ]

    def get_has_result(self, obj):
        return hasattr(obj, 'analysis_result')


class AnalysisResultSerializer(serializers.ModelSerializer):
    video_upload_id = serializers.IntegerField(source='video.id', read_only=True)
    title = serializers.CharField(source='video.title', read_only=True)
    status = serializers.CharField(source='video.status', read_only=True)
    uploaded_at = serializers.DateTimeField(source='video.uploaded_at', read_only=True)
    duration = serializers.FloatField(source='video.duration', read_only=True)
    frame_count = serializers.IntegerField(source='video.frame_count', read_only=True)
    fps = serializers.FloatField(source='video.fps', read_only=True)
    video_file_url = serializers.SerializerMethodField()

    conclusion = serializers.SerializerMethodField()
    core_metrics = serializers.SerializerMethodField()
    suggestions = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()
    trend_series = serializers.SerializerMethodField()

    summary = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisResult
        fields = [
            'video_upload_id',
            'title',
            'status',
            'uploaded_at',
            'duration',
            'frame_count',
            'fps',
            'video_file_url',
            'issues',
            'overall_metrics',
            'summary',
            'conclusion',
            'core_metrics',
            'suggestions',
            'trend_series',
            'review',
            'actions',
            'analyzed_at',
        ]

    def get_video_file_url(self, obj):
        request = self.context.get('request')
        if not obj.video.video_file:
            return None
        url = obj.video.video_file.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_summary(self, obj):
        metrics = obj.overall_metrics or {}
        return {
            'cadence': metric_value(metrics, 'cadence'),
            'ground_contact_time': metric_value(metrics, 'ground_contact_time'),
            'flight_time': metric_value(metrics, 'flight_time'),
            'vertical_oscillation_rel': metric_value(metrics, 'vertical_oscillation_rel'),
            'trunk_lean_angle': metric_value(metrics, 'trunk_lean_angle'),
            'overstride_index': metric_value(metrics, 'overstride_index'),
        }

    def get_conclusion(self, obj):
        return derive_conclusion(obj.issues or [], obj.overall_metrics or {})

    def get_core_metrics(self, obj):
        metrics = obj.overall_metrics or {}

        config = [
            ('cadence', '步频', 'spm'),
            ('ground_contact_time', '触地时间', 'ms'),
            ('flight_time', '腾空时间', 'ms'),
            ('vertical_oscillation_rel', '垂直振幅', ''),
            ('trunk_lean_angle', '躯干前倾角', 'deg'),
            ('overstride_index', '过度跨步指数', ''),
        ]

        items = []
        for key, label, fallback_unit in config:
            value = metric_value(metrics, key)
            unit = metric_unit(metrics, key, fallback_unit)
            confidence = metric_confidence(metrics, key)

            items.append({
                'key': key,
                'label': label,
                'value': value,
                'unit': unit,
                'confidence': confidence,
                'display_value': format_metric_display(value, unit),
            })
        return items

    def get_suggestions(self, obj):
        return derive_suggestions(obj.issues or [])

    def get_trend_series(self, obj):
        return build_trend_series(obj.overall_metrics or {})

    def get_review(self, obj):
        duration_seconds = getattr(obj.video, "duration", None)
        frames = sample_pose_frames(
            obj.pose_data or [],
            duration_seconds=duration_seconds
        )
        has_any_landmarks = any(f.get("landmarks") for f in frames)

        return {
            'video_url': self.get_video_file_url(obj),
            'has_pose_data': bool(obj.pose_data),
            'pose_frame_count': len(obj.pose_data or []),
            'has_2d_overlay': has_any_landmarks,
            'has_3d_overlay': any(f.get("landmarks_3d") for f in frames),
            'frames': frames,
        }

    def get_actions(self, obj):
        return {
            'history_id': obj.video.id,
            'can_reanalyze': True,
            'can_open_history': True,
            'can_go_home': True,
        }