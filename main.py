
import customtkinter as ctk

import gemini
import paste
import recording


# アプリの初期設定
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Gemini　AI薬歴")
app.geometry("500x900")
app.attributes('-topmost', True)

# ======= ROW / COLUMN CONFIG ==========
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)


# =======  ログ表示（スクロール付き） ==========
log_label = ctk.CTkLabel(app, text="ログ：")
log_label.grid(row=8, column=0, padx=10, pady=(10, 0), sticky="w")

log_box = ctk.CTkTextbox(app, height=200)
log_box.grid(row=9, column=0, padx=10, pady=10, sticky="nsew")

def log_write(text):
    log_box.insert("end", text)

# 関数
def recording_start():
    text = recording.recording_start()
    log_write(text)

def recording_stop():
    text = recording.recording_stop()
    log_write(text)

def summarize():
    gemini.summarize()

def auto_paste():
    paste.auto_paste()



# ======= 1. 録音・停止ボタン ==========
frame_buttons = ctk.CTkFrame(app)
frame_buttons.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
frame_buttons.grid_columnconfigure((0, 1), weight=0)

btn_record = ctk.CTkButton(frame_buttons, text="録音")
btn_record.grid(row=0, column=0, padx=5, pady=5)

btn_stop = ctk.CTkButton(frame_buttons, text="停止")
btn_stop.grid(row=0, column=1, padx=5, pady=5)

# ======= 2. ドロップダウン ==========
dropdown_label = ctk.CTkLabel(app, text="選択：")
dropdown_label.grid(row=1, column=0, padx=10, sticky="w")

dropdown = ctk.CTkComboBox(app, values=["A", "B", "C"])
dropdown.grid(row=2, column=0, padx=10, sticky="ew")

# ======= 3. インプットボックス ==========
input_label = ctk.CTkLabel(app, text="メモ：")
input_label.grid(row=3, column=0, padx=10, pady=(15, 0), sticky="w")

input_box = ctk.CTkEntry(app)
input_box.grid(row=4, column=0, padx=10, sticky="ew")

# ======= 4. テキストボックス（複数行） ==========
text_label = ctk.CTkLabel(app, text="テキスト入力：")
text_label.grid(row=5, column=0, padx=10, pady=(15, 0), sticky="w")

text_box = ctk.CTkTextbox(app, height=150)
text_box.grid(row=6, column=0, padx=10, sticky="ew")

# ======= 5. ボタン2つ（実行、クリア） ==========
frame_exec = ctk.CTkFrame(app)
frame_exec.grid(row=7, column=0, padx=10, pady=10, sticky="ew")
frame_exec.grid_columnconfigure((0, 1), weight=0)

btn_run = ctk.CTkButton(frame_exec, text="実行")
btn_run.grid(row=0, column=0, padx=5, pady=5)

btn_clear = ctk.CTkButton(frame_exec, text="クリア")
btn_clear.grid(row=0, column=1, padx=5, pady=5)



if __name__ == "__main__":
    app.mainloop()