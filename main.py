from datetime import date
import threading

import customtkinter as ctk

from services.gemini import Gemini
from services.recording import Recorder
from services.paste import AutoGui
from services.db_oparation import DBOperator
import settings.widgets


ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db_operator = DBOperator()
        self.db_thread = None

        self.is_recording = False
        self.recording_thread = None
        self.recording_stop_event = threading.Event()
        self.recorder = Recorder(self.recording_stop_event)

        self.gemini = Gemini()
        self.gemini_thread = None

        self.autogui = AutoGui()

        self.title("Gemini　AI薬歴")
        self.geometry("500x900")
        self.attributes('-topmost', True)

        # ★ ウィンドウ全体の grid 設定
        # 横方向：col=0 を伸ばす（ただし中身のwidgetはstickyで制御）
        self.grid_columnconfigure(0, weight=1)
        # 縦方向：row=4（summaryのフレーム）だけ伸ばす
        self.grid_rowconfigure(4, weight=1)

        # ウィジェット（上から順番）
        self.btn_record_start = None
        self.btn_record_stop = None
        self.dropdown_label = None
        self.dropdown = None
        self.btn_add_name = None
        self.btn_delete_name = None
        self.date_selector = None
        self.memo_label = None
        self.memo_input_box = None
        self.dropdown_summary = None
        self.btn_load_summaries = None
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
            width=100, height=40
        )
        self.btn_record_start.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # 録音停止ボタン
        self.btn_record_stop = ctk.CTkButton(
            self.flame_btn_recorder,
            text="停止",
            state='disabled',
            command=self.stop_recording,
            width=100, height=40
        )
        self.btn_record_stop.grid(row=0, column=1, padx=5, pady=5, sticky="w")


        # ===== 名前一覧 =====
        names_list = self.db_operator.load_names_list()
        names_list.insert(0, '')

        self.flame_pharmacists = ctk.CTkFrame(self)
        self.flame_pharmacists.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # 名前のドロップダウン
        self.dropdown_label = ctk.CTkLabel(self.flame_pharmacists, text="投薬者")
        self.dropdown_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")
        self.dropdown = ctk.CTkComboBox(self.flame_pharmacists, values=names_list)
        self.dropdown.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")

        # 名前新規追加
        self.btn_add_name = ctk.CTkButton(
            self.flame_pharmacists,
            text='投薬者登録',
            command=lambda: self.add_name(self.dropdown.get()),
            width=80, height=28,
        )
        self.btn_add_name.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # 名前削除
        self.btn_delete_name = ctk.CTkButton(
            self.flame_pharmacists,
            text='投薬者削除',
            command=lambda: self.delete_name(self.dropdown.get()),
            width=80, height=28,
            fg_color="transparent",  # 背景なし
            border_color="#666666",
            border_width=1,
            text_color="#444444",
            hover_color="#DDDDDD",
        )
        self.btn_delete_name.grid(row=1, column=2, padx=5, pady=5, sticky="w")


        # ===== メモ =====
        self.flame_memo = ctk.CTkFrame(self)
        self.flame_memo.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.flame_memo.grid_columnconfigure(1, weight=1)

        self.date_selector = settings.widgets.DateSelector(
            self.flame_memo,
            retention_days=7,
        )
        self.date_selector.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="w")

        self.memo_label = ctk.CTkLabel(self.flame_memo, text="メモ：")
        self.memo_label.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")

        self.memo_input_box = settings.widgets.NumberEntry(
            self.flame_memo,
            placeholder_text='メモ',
            min_value=0,
            max_value=500,
            step=1
        )
        self.memo_input_box.grid(row=1, column=1, padx=(0, 10), pady=5, sticky="w")


        # ===要約再読み込み===
        summaries_list = self.db_operator.load_summary()
        summaries_title_list = [
            f"{created_at} / {name or ''} / {memo or ''}"
            for (_id, name, memo, _content, created_at) in summaries_list
        ]
        summaries_title_list.insert(0, '')

        self.flame_load_summaries = ctk.CTkFrame(self)
        self.flame_load_summaries.grid(row=3, column=0, padx=5, pady=5, sticky="w")

        self.dropdown_summary = ctk.CTkComboBox(self.flame_load_summaries, values=summaries_title_list)
        self.dropdown_summary.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_load_summaries = ctk.CTkButton(
            self.flame_load_summaries,
            width=200, height=30,
            text='要約の読み込み（日付指定）',
        )
        self.btn_load_summaries.grid(row=0, column=1, padx=5, pady=5, sticky="w")


        # ===== 要約（ここだけリサイズ対象） =====
        self.flame_summary = ctk.CTkFrame(self)
        self.flame_summary.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")
        self.flame_summary.grid_columnconfigure(0, weight=1)  # 横方向
        self.flame_summary.grid_rowconfigure(1, weight=1)     # summary_text_box の行

        self.summary_label = ctk.CTkLabel(self.flame_summary, text="要約：")
        self.summary_label.grid(row=0, column=0, padx=5, pady=(5, 0), sticky="w")

        self.summary_date_text_box = ctk.CTkLabel(
            self.flame_summary,
            text=summaries_title_list[0]
        )
        self.summary_date_text_box.grid(row=0, column=1, padx=5, pady=(5, 0), sticky="w")

        self.summary_text_box = ctk.CTkTextbox(self.flame_summary, height=150)
        self.summary_text_box.grid(row=1, column=0, padx=10, sticky="nsew")

        self.btn_paste = ctk.CTkButton(
            self.flame_summary,
            text="自動ペースト",
            command=self.auto_paste,
        )
        self.btn_paste.grid(row=2, column=0, padx=5, pady=5, sticky="w")


        # ===== ログ =====
        self.flame_log = ctk.CTkFrame(self)
        self.flame_log.grid(row=5, column=0, padx=5, pady=5, sticky="ew")
        self.flame_log.grid_columnconfigure(0, weight=1)

        self.log_label = ctk.CTkLabel(self.flame_log, text="ログ：")
        self.log_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.log_box = ctk.CTkTextbox(self.flame_log, height=100)
        self.log_box.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")


    # ====== 関数 ======
    def log(self, text: str):
        """ログ出力"""
        self.log_box.insert("1.0", f'{text}\n')
        self.log_box.update()

    def add_name(self, name: str):
        name = name.strip()
        if not name:
            self.log('登録する名前が選択されていません。')
            return
        self.db_operator.add_name(name)
        self.log(f'{name}を追加しました。')
        names_list = self.db_operator.load_names_list()
        names_list.insert(0, '')
        self.dropdown.configure(values=names_list)
        self.dropdown.set(name)

    def delete_name(self, name: str):
        name = name.strip()
        if not name:
            self.log('削除する名前が選択されていません。')
            return
        self.db_operator.delete_name(name)
        self.log(f'{name}を削除しました。')
        names_list = self.db_operator.load_names_list()
        names_list.insert(0, '')
        self.dropdown.configure(values=names_list)

        if len(names_list) > 1:
            self.dropdown.set(names_list[1])
        else:
            self.dropdown.set('')

    def load_summaries_list(self):
        # 例： '2025-11-23' という文字列が入っている
        target_date = self.date_selector.get().strip()

        if target_date:
            summaries_list = self.db_operator.load_summary(target_date)
        else:
            today_str = date.today().strftime('%Y-%m-%d')
            summaries_list = self.db_operator.load_summary(today_str)  # 全件

        # ドロップダウン表示用に整形
        dropdown_values = [
            f"{created_at} / {name or ''} / {memo or ''}"
            for (_id, name, memo, _content, created_at) in summaries_list
        ]
        dropdown_values.insert(0, '')

        self.log(f'{target_date}の要約を読み込みました。')
        self.dropdown_summary.configure(values=dropdown_values)

    def start_recording(self):
        """threadにて録音開始 """
        if self.is_recording:
            return

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
        録音停止 -> gemini_thread開始
        """
        if not self.is_recording:
            return
        self.log('録音を停止しました。')
        self.is_recording = False
        self.recording_stop_event.set()
        if self.recording_thread is not None:
            self.recording_thread.join()
            self.recording_thread = None

        self.btn_record_stop.configure(state='disabled')
        self.btn_record_start.configure(state='normal')

        recorded_file = self.recorder.recording_stop()

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
                name = self.dropdown.get().strip()
                memo = self.memo_input_box.get().strip()
                self.after(0, self._update_summary_text, summarized_text)
                self.after(0, self.log, '要約が完了しました。')
                self.db_thread = threading.Thread(
                    target=self.db_operator.save_summary,
                    args=(summarized_text, name, memo,),
                    daemon=True
                )

        except Exception as e:
            self.after(0,self.log, f'要約エラー：{e}')

    def auto_paste(self):
        text = self.summary_text_box.get('1.0', 'end-1c')
        self.log('自動ペーストしています。')
        result = self.autogui.paste(text)
        if result.get('status') == 'success':
            self.log(result.get('message'))
        else:
            self.log(f"自動ペーストエラー: {result.get('message')}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
