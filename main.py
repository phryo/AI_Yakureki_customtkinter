import threading

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

        self.is_recording = False
        self.recording_thread = None
        self.recording_stop_event = threading.Event()
        self.gemini_thread = None

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
        """
        UI作成
        """
        # ===== 録音ボタン =====
        self.flame_btn_recorder = ctk.CTkFrame(self)
        self.flame_btn_recorder.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_record_start = ctk.CTkButton(
            self.flame_btn_recorder,
            text="録音",
            command=self.start_recording,
        )
        self.btn_record_start.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_record_stop = ctk.CTkButton(
            self.flame_btn_recorder,
            text="停止",
            state='disabled',
            command=lambda: self.stop_recording(self.recording_stop_event),
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
            command=self.auto_paste,
        )
        self.btn_paste.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        # ===== ログ =====
        self.flame_log = ctk.CTkFrame(self)
        self.flame_log.grid(row=4, column=0, padx=5, pady=5, sticky="ew")
        self.flame_log.grid_columnconfigure(0, weight=1)

        self.log_label = ctk.CTkLabel(self.flame_log, text="ログ：")
        self.log_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")

        self.log_box = ctk.CTkTextbox(self.flame_log, height=100)
        self.log_box.grid(row=1, column=0, padx=10, pady=10, sticky="ew")


    # ====== 関数 ======
    def log(self, text: str):
        """ログ出力"""
        self.log_box.insert("end", f'{text}\n')
        self.log_box.see("end")
        self.log_box.update()

    def start_recording(self):
        """threadにて録音開始 """
        self.log('録音を開始します。')
        self.is_recording = True
        self.recording_stop_event.clear()

        self.btn_record_start.configure(state='disabled')
        self.btn_record_stop.configure(state='normal')

        self.recording_thread = threading.Thread(
            target=self.recorder.recording_start,
            args=(self.recording_stop_event,),
            daemon=True)
        self.recording_thread.start()

    def stop_recording(self):
        """
        録音停止
        :return:gemini_thread開始
        """
        if not self.is_recording:
            return
        self.log('録音を停止しました。')
        self.is_recording = False
        self.recording_stop_event.set()
        self.recording_thread.join()

        self.btn_record_stop.configure(state='disabled')
        self.btn_record_start.configure(state='normal')

        recorded_file = self.recorder.recording_stop(
            stop_event=self.recording_stop_event)

        if recorded_file.get('status') == 'success':
            file_path = recorded_file.get('file_path')
            self.gemini_thread = threading.Thread(
                target=self.gemini_task,
                args=(file_path,),
                daemon=True)
            self.gemini_thread.start()
        else:
            self.log(recorded_file.get('message'))

    def _update_summary_text(self, text: str):
        """要約結果をテキストボックスに反映（メインスレッドで実行）"""
        self.summary_text_box.delete('1.0', 'end')
        self.summary_text_box.insert('1.0', text)

    def gemini_task(self, recorded_file):
        """録音したファイルをGeminiに投げて要約する"""
        try:
            result = self.gemini.summarize(recorded_file)

            if result.get('status') == 'success':
                summarized_text = result.get('summary')
                self.after(0, self._update_summary_text, summarized_text)
                self.after(0, self.log, '要約が完了しました。')

        except Exception as e:
            self.after(0,self.log, f'要約エラー：{e}')

    def auto_paste(self):
        text = self.summary_text_box.get('1.0', 'end-1c')
        self.log('自動ペーストしています。')
        self.autogui.paste(text)
        self.log('自動ペーストが完了しました。')

if __name__ == "__main__":
    app = App()
    app.mainloop()
