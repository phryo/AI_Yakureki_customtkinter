DB_NAME = 'summaries.db'

SAMPLERATE = 44100  # サンプリングレート
CHANNELS = 1  # チャンネル数
DTYPE = 'int16'  # データ型
WAVE_OUTPUT_FILENAME = 'recording.wav'  # 保存ファイル名

with open('prompt.txt', 'r', encoding='utf-8') as f:
    PROMPT = f.read()