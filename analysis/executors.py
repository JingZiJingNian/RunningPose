import os
import sys
import subprocess
from pathlib import Path


def schedule_analysis(video_upload_id: int) -> None:
    """
    启动一个独立后台进程执行分析任务。
    当前版本不依赖 Redis/Celery，适合作为本地开发过渡方案。
    """
    project_root = Path(__file__).resolve().parent.parent
    manage_py = project_root / 'manage.py'

    cmd = [
        sys.executable,
        str(manage_py),
        'run_analysis_job',
        str(video_upload_id),
    ]

    kwargs = {
        'cwd': str(project_root),
        'stdout': subprocess.DEVNULL,
        'stderr': subprocess.DEVNULL,
        'stdin': subprocess.DEVNULL,
        'close_fds': True,
    }

    if os.name == 'nt':
        creationflags = 0
        creationflags |= getattr(subprocess, 'DETACHED_PROCESS', 0)
        creationflags |= getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
        kwargs['creationflags'] = creationflags
    else:
        kwargs['start_new_session'] = True

    subprocess.Popen(cmd, **kwargs)