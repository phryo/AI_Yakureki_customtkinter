import platform
from pathlib import Path


# if platform.system() == "Windows":
#     BASE_DIR = Path(r"\\Toridesvr01\取手\06_マニュアル・ 書類フォーマット\AI-薬歴")
# else:
#     BASE_DIR = Path(__file__).resolve().parent.parent

BASE_DIR = Path(r"C:\Users\sakur\PycharmProjects\AI_Yakureki_customtkinter")

# db_operation.py
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