import customtkinter as ctk

from services.gemini import Gemini
from services.recording import Recorder
from services.paste import AutoGui
from services.db_oparation import DBOperator


ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db_operator = DBOperator()
        self.gemini = Gemini()
        self.recorder = Recorder()
        self.autogui = AutoGui()

        self.title("Gemini　AI薬歴")
        self.geometry("500x900")
        self.attributes('-topmost', True)

        # ★ ウィンドウ全体の grid 設定
        # 横方向：col=0 を伸ばす（ただし中身のwidgetはstickyで制御）
        self.grid_columnconfigure(0, weight=1)
        # 縦方向：row=3（summaryのフレーム）だけ伸ばす
        self.grid_rowconfigure(3, weight=1)

        self.btn_record_start = None
        self.btn_record_stop = None
        self.dropdown_label = None
        self.dropdown = None
        self.btn_registration_name = None
        self.memo_label = None
        self.memo_input_box = None
        self.summary_label = None
        self.summary_text_box = None
        self.btn_paste = None
        self.log_label = None
        self.log_box = None
        self.create_widgets()

    def create_widgets(self):
        # ===== 録音ボタン =====
        self.flame_btn_recorder = ctk.CTkFrame(self)
        self.flame_btn_recorder.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_record_start = ctk.CTkButton(
            self.flame_btn_recorder,
            text="録音",
            command=self.recorder.recording_start,
        )
        self.btn_record_start.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_record_stop = ctk.CTkButton(
            self.flame_btn_recorder,
            text="停止",
            command=self.recorder.recording_stop,
        )
        self.btn_record_stop.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # ===== 名前一覧 =====
        pharmacists_list = self.db_operator.load_pharmacists_list()
        self.flame_pharmacists = ctk.CTkFrame(self)
        self.flame_pharmacists.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.dropdown_label = ctk.CTkLabel(self.flame_pharmacists, text="投薬者：")
        self.dropdown_label.grid(row=0, column=0, padx=10, sticky="w")

        self.dropdown = ctk.CTkComboBox(self.flame_pharmacists, values=pharmacists_list)
        # 横幅を固定にしたいなら sticky="w" にする
        self.dropdown.grid(row=1, column=0, padx=10, sticky="w")

        self.btn_registration_name = ctk.CTkButton(
            self.flame_pharmacists,
            text='投薬者登録',
            command=self.db_operator.registration_name,
        )
        self.btn_registration_name.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # ===== メモ =====
        self.flame_memo = ctk.CTkFrame(self)
        self.flame_memo.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.memo_label = ctk.CTkLabel(self.flame_memo, text="メモ：")
        self.memo_label.grid(row=0, column=0, padx=10, pady=(15, 0), sticky="w")

        self.memo_input_box = ctk.CTkEntry(self.flame_memo)
        # 横幅も固定にしたいなら sticky="w"
        self.memo_input_box.grid(row=1, column=0, padx=10, sticky="w")

        # ===== 要約（ここだけリサイズ対象） =====
        self.flame_summary = ctk.CTkFrame(self)
        self.flame_summary.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        self.flame_summary.grid_columnconfigure(0, weight=1)  # 横方向
        self.flame_summary.grid_rowconfigure(1, weight=1)     # summary_text_box の行

        self.summary_label = ctk.CTkLabel(self.flame_summary, text="テキスト入力：")
        self.summary_label.grid(row=0, column=0, padx=10, pady=(15, 0), sticky="w")

        self.summary_text_box = ctk.CTkTextbox(self.flame_summary, height=150)
        # ★ 横も縦も伸びてほしいので nsew
        self.summary_text_box.grid(row=1, column=0, padx=10, sticky="nsew")

        self.btn_paste = ctk.CTkButton(
            self.flame_summary,
            text="自動ペースト",
            command=self.autogui.paste,
        )
        self.btn_paste.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        # ===== ログ =====
        self.flame_log = ctk.CTkFrame(self)
        self.flame_log.grid(row=4, column=0, padx=5, pady=5, sticky="ew")
        self.flame_log.grid_columnconfigure(0, weight=1)

        self.log_label = ctk.CTkLabel(self.flame_log, text="ログ：")
        self.log_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")

        self.log_box = ctk.CTkTextbox(self.flame_log, height=100)
        # 横も固定にしたいなら sticky="w"
        self.log_box.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

    def log_write(self, text: str):
        self.log_box.insert("end", text)


if __name__ == "__main__":
    app = App()
    app.mainloop()
