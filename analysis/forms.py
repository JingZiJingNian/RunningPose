from django import forms
from .models import VideoUpload


class VideoUploadForm(forms.ModelForm):
    class Meta:
        model = VideoUpload
        fields = ['title', 'video_file', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.HiddenInput(),
            'end_time': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['start_time'].required = False
        self.fields['end_time'].required = False

        self.fields['title'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '请输入视频标题',
            'id': 'id_title'
        })
        self.fields['video_file'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'video/*',
            'id': 'id_video_file'
        })

    def clean_video_file(self):
        video_file = self.cleaned_data.get('video_file')
        if not video_file:
            raise forms.ValidationError('请选择视频文件')

        if video_file.size > 100 * 1024 * 1024:
            raise forms.ValidationError('视频文件大小不能超过100MB')

        valid_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        filename = video_file.name.lower()
        if not any(filename.endswith(ext) for ext in valid_extensions):
            raise forms.ValidationError('请上传有效的视频文件（MP4, MOV, AVI, MKV, WEBM）')

        return video_file

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time in (None, ''):
            start_time = 0
        if end_time in ('',):
            end_time = None

        try:
            start_time = float(start_time)
        except (TypeError, ValueError):
            raise forms.ValidationError('开始时间格式不正确')

        if end_time is not None:
            try:
                end_time = float(end_time)
            except (TypeError, ValueError):
                raise forms.ValidationError('结束时间格式不正确')

        if start_time < 0:
            raise forms.ValidationError('开始时间不能小于 0 秒')

        if end_time is not None:
            if end_time <= start_time:
                raise forms.ValidationError('结束时间必须大于开始时间')
            if (end_time - start_time) < 5:
                raise forms.ValidationError('分析时间段必须至少 5 秒')

        cleaned_data['start_time'] = start_time
        cleaned_data['end_time'] = end_time
        return cleaned_data