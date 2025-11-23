# db_operation.py
DB_NAME = 'summaries.db'

# recording.py
SAMPLERATE = 44100  # サンプリングレート
CHANNELS = 1  # チャンネル数
DTYPE = 'int16'  # データ型
WAVE_OUTPUT_FILENAME = 'recording.wav'  # 保存ファイル名

# prompt.txt
with open('prompt.txt', 'r', encoding='utf-8') as f:
    PROMPT = f.read()

# paste.py
SECTION_MAPPING = [
    ('/', '服用状況'),
    ('*', '体調変化'),
    ('7', 'S/O（患者）'),
    ('4', 'A/P（指導）'),
    ('k', '計画'),
]