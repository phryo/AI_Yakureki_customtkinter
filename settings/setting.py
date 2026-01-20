import platform
import sys
from pathlib import Path


# db_operation.py
def app_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent
CONFIG_DIR = app_dir() / 'データ保管場所.txt'
try:
    raw = CONFIG_DIR.read_text(encoding='utf-8-sig').strip()
    BASE_DIR = Path(raw)
    if not raw:
        raise ValueError('データ保管場所.txtが空です。')
except FileNotFoundError:
    BASE_DIR = app_dir()
DB_PATH = BASE_DIR / 'summaries.db'
PROMPT_PATH = BASE_DIR / 'prompt.txt'


# recording.py
SAMPLERATE = 44100  # サンプリングレート
CHANNELS = 1  # チャンネル数
DTYPE = 'int16'  # データ型
WAVE_OUTPUT_FILENAME = 'recording.wav'  # 保存ファイル名

MAX_RECORDING_SECONDS = 300

# prompt.txt
with PROMPT_PATH.open('r', encoding='utf-8') as f:
    PROMPT = f.read()

# paste.py
SECTION_MAPPING = [
    ('/', '服薬状況'),
    ('*', '体調変化'),
    ('7', 'S/O（患者）'),
    ('4', 'A/P（指導）'),
    ('k', '計画'),
]