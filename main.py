import json
import os
import time
from datetime import date
import threading
import tkinter
import queue

import customtkinter as ctk

from services.gemini import Gemini
from services.recording import Recorder
from services.paste import AutoGui
from services.db_oparation import DBOperator
import settings.setting
import settings.widgets


ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db_operator = DBOperator()
        self.db_thread = None

        self.bind("<F1>", self.on_f1)

        self.is_recording = False
        self.recording_thread = None
        self.recording_stop_event = threading.Event()
        self.recorder = Recorder(self.recording_stop_event)

        self.record_start_time = None
        self.record_time_seconds = 0
        self.record_timer_id = None
        self.max_record_seconds = settings.setting.MAX_RECORDING_SECONDS

        self.gemini = Gemini()
        # ★ Gemini 用キュー & ワーカースレッド
        self.gemini_queue = queue.Queue()
        self.gemini_worker_thread = threading.Thread(
            target=self._gemini_worker,
            daemon=True
        )
        self.gemini_worker_thread.start()

        self.autogui = AutoGui()

        self.title("Gemini　AI薬歴")
        self.geometry("500x900")
        # self.attributes('-topmost', True)

        # ★ ウィンドウ全体の grid 設定
        # 横方向：col=0 を伸ばす（ただし中身のwidgetはstickyで制御）
        self.grid_columnconfigure(0, weight=1)
        # 縦方向：row=4（summaryのフレーム）だけ伸ばす
        self.grid_rowconfigure(4, weight=1)

        # 辞書、リスト
        self.names_list = self.db_operator.load_names_list()

        # 選択中の投薬者
        self.selected_name = self.names_list[0] if self.names_list else ""

        self.summaries_dict = {}

        self.current_summary_id = None
        self.selected_current_content = None

        # ウィジェット（上から順番）
        self.btn_record_start = None
        self.btn_record_stop = None
        self.lbl_timer = None
        self.name_button_frame = None
        self.name_buttons: dict[str, ctk.CTkButton] = {}
        self.name_entry = None
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
        self.btn_update_summary = None
        self.log_label = None
        self.log_box = None

        self.create_widgets()

    def create_widgets(self):
        """
        UI作成
        """
        # ===== 録音ボタン =====
        self.frame_btn_recorder = ctk.CTkFrame(self)
        self.frame_btn_recorder.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_record_start = ctk.CTkButton(
            self.frame_btn_recorder,
            text="録音(F1)",
            fg_color="#1f6aa5",  # 通常時の色
            hover_color="#144870",
            text_color="white",
            font=("Arial", 15, "bold"),
            command=self.start_recording,
            width=100, height=40
        )
        self.btn_record_start.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # 録音停止ボタン
        self.btn_record_stop = ctk.CTkButton(
            self.frame_btn_recorder,
            text="停止(F1)",
            state="disabled",
            font=("Arial", 15, "bold"),
            command=self.stop_recording,
            width=100, height=40
        )
        self.btn_record_stop.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # 録音時間表示ラベル
        self.lbl_timer = ctk.CTkLabel(
            self.frame_btn_recorder,
            text="00:00",
            font=("Arial", 20, "bold"),
            width=100, height=40
        )
        self.lbl_timer.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # ===== 名前一覧 =====
        self.frame_pharmacists = ctk.CTkFrame(self)
        self.frame_pharmacists.grid(row=1, column=0, padx=5, pady=5, sticky="we")
        self.frame_pharmacists.grid_columnconfigure(0, weight=1)

        self.name_button_frame = ctk.CTkScrollableFrame(
            self.frame_pharmacists, orientation="horizontal", height=42
        )
        self.name_button_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="we")
        self.frame_pharmacists.grid_columnconfigure(0, weight=1)

        self.render_name_buttons()

        self.name_entry = ctk.CTkEntry(
            self.frame_pharmacists,
            placeholder_text="投薬者名を入力",
            width=160
        )
        self.name_entry.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="w")

        # 名前新規追加
        self.btn_add_name = ctk.CTkButton(
            self.frame_pharmacists,
            text="投薬者登録",
            command=self.add_name,
            width=80, height=28,
        )
        self.btn_add_name.grid(row=2, column=1, padx=5, pady=(0, 5), sticky="w")

        # 名前削除
        self.btn_delete_name = ctk.CTkButton(
            self.frame_pharmacists,
            text='投薬者削除',
            command=self.delete_name,
            width=80, height=28,
            fg_color="transparent",  # 背景なし
            border_color="#666666",
            border_width=1,
            text_color="#444444",
            hover_color="#DDDDDD",
        )
        self.btn_delete_name.grid(row=2, column=2, padx=5, pady=(0, 5), sticky="w")


        # ===== メモ =====
        self.frame_memo = ctk.CTkFrame(self)
        self.frame_memo.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.frame_memo.grid_columnconfigure(1, weight=1)

        self.date_selector = settings.widgets.DateSelector(
            self.frame_memo,
            retention_days=7,
        )
        self.date_selector.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="w")

        self.memo_label = ctk.CTkLabel(self.frame_memo, text="メモ：")
        self.memo_label.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")

        self.memo_input_box = settings.widgets.NumberEntry(
            self.frame_memo,
            placeholder_text="メモ",
            min_value=0,
            max_value=500,
            step=1
        )
        self.memo_input_box.grid(row=1, column=1, padx=(0, 10), pady=5, sticky="w")


        # ===要約再読み込み===
        today_str = date.today().strftime('%Y-%m-%d')
        summaries_list = self.db_operator.load_summary(today_str)
        summaries_title_list = [
            f"{created_at[5:].replace('-', '/')} | {memo or ''}"
            for (_id, name, memo, _content, created_at) in summaries_list
        ]

        self.frame_load_summaries = ctk.CTkFrame(self)
        self.frame_load_summaries.grid(row=3, column=0, padx=5, pady=5, sticky="w")

        self.dropdown_summary = settings.widgets.CenteredDropdown(
            self.frame_load_summaries,
            values=summaries_title_list,
            command=self.on_selected_summary
        )
        self.dropdown_summary.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_load_summaries = ctk.CTkButton(
            self.frame_load_summaries,
            width=200, height=30,
            text="要約の読み込み（日付、名前指定）",
            command=self.load_summaries_list
        )
        self.btn_load_summaries.grid(row=0, column=1, padx=5, pady=5, sticky="w")


        # ===== 要約（ここだけリサイズ対象） =====
        self.frame_summary = ctk.CTkFrame(self)
        self.frame_summary.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")
        self.frame_summary.grid_columnconfigure(0, weight=1)  # 横方向
        self.frame_summary.grid_rowconfigure(0, weight=1)     # summary_text_box の行

        self.summary_text_box = ctk.CTkTextbox(self.frame_summary, height=150)
        self.summary_text_box.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="nsew")

        self.frame_btn_in_summary = ctk.CTkFrame(self.frame_summary,
                                                 fg_color="transparent",
                                                 border_width=0,)
        self.frame_btn_in_summary.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # 自動ペーストボタン
        self.btn_paste = ctk.CTkButton(
            self.frame_btn_in_summary,
            text="自動ペースト",
            command=self.auto_paste
        )
        self.btn_paste.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # 要約保存ボタン
        self.btn_update_summary = ctk.CTkButton(
            self.frame_btn_in_summary,
            text="保存",
            width=50,
            command=self.update_summary
        )
        self.btn_update_summary.grid(row=0, column=1, padx=5, pady=5, sticky="w")


        # ===== ログ =====
        self.frame_log = ctk.CTkFrame(self)
        self.frame_log.grid(row=5, column=0, padx=5, pady=5, sticky="ew")
        self.frame_log.grid_columnconfigure(0, weight=1)

        self.log_label = ctk.CTkLabel(self.frame_log, text="ログ：")
        self.log_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.log_box = ctk.CTkTextbox(self.frame_log, height=70)
        self.log_box.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")


    # ====== 関数 ======
    def on_f1(self, event=None):
        self.toggle_recording()

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    # ログ表示
    def log(self, text: str):
        """ログ出力"""
        self.log_box.insert("1.0", f'{text}\n')
        self.log_box.update()

    # 投薬者関連
    def render_name_buttons(self):
        for btn in self.name_buttons.values():
            btn.destroy()
        self.name_buttons.clear()

        for idx, name in enumerate(self.names_list):
            btn = ctk.CTkButton(
                self.name_button_frame,
                text=name,
                width=60,
                command=lambda n=name: self.select_name(n),
                corner_radius=8,
                height=32
            )
            btn.grid(row=0, column=idx, padx=5, pady=5, sticky="w")
            self.name_buttons[name] = btn

        self.update_name_button_styles()

    def select_name(self, name: str):
        self.selected_name = name
        self.update_name_button_styles()

    def update_name_button_styles(self):
        for name, btn in self.name_buttons.items():
            if name == self.selected_name:
                btn.configure(fg_color="#1f6aa5", text_color="white", border_width=0)
            else:
                btn.configure(fg_color="transparent", border_color="#666666", border_width=1, text_color="#444444")

    def add_name(self):
        name = self.name_entry.get().strip()
        if not name:
            self.log('登録する名前が入力されていません。')
            return
        self.db_operator.add_name(name)
        self.log(f'{name}を追加しました。')
        self.names_list = self.db_operator.load_names_list()
        self.selected_name = name
        self.name_entry.delete(0, "end")
        self.render_name_buttons()

    def delete_name(self):
        """投薬者の削除"""
        name = self.name_entry.get().strip() or self.selected_name
        if not name:
            self.log('削除する名前が選択されていません。')
            return
        possible_delete = tkinter.messagebox.askokcancel(
            '確認',
            '本当に削除してもよろしいですか？'
        )
        if not possible_delete:
            return
        self.db_operator.delete_name(name)
        self.log(f'{name}を削除しました。')
        self.names_list = self.db_operator.load_names_list()

        self.selected_name = self.names_list[0] if self.names_list else ""
        self.render_name_buttons()

    # 要約関連
    def load_summaries_list(self):
        """要約のリストをDBから読み込む"""
        # 例： '2025-11-23' という文字列が入っている
        target_date = self.date_selector.get_date_str().strip()
        name = self.selected_name

        if target_date:
            summaries_list = self.db_operator.load_summary(target_date, name)
        else:
            today_str = date.today().strftime('%Y-%m-%d')
            summaries_list = self.db_operator.load_summary(today_str, name)

        self.summaries_dict = {
            f"{created_at[5:].replace('-', '/')} | {memo or ''}": {
                "id": _id,
                "content": content}
            for (_id, _name, memo, content, created_at) in summaries_list
        }

        # ドロップダウン表示用に整形
        dropdown_values = list(sorted(self.summaries_dict.keys(), reverse=True))

        self.log(f'{target_date} | {name}の要約を読み込みました。')
        self.dropdown_summary.configure_values(dropdown_values)

    def on_selected_summary(self, selected_label: str):
        """ドロップダウンで要約を選択したときに呼ばれる"""
        data = self.summaries_dict.get(selected_label)
        if not data:
            self.log('要約データが取得できませんでした。')
            return

        self.current_summary_id = data.get("id")
        selected_current_content = data.get("content")

        self.summary_text_box.delete("1.0", "end")
        self.summary_text_box.insert("end", selected_current_content)

    def _update_summary_text(self, text: str):
        """要約結果をテキストボックスに反映（メインスレッドで実行）"""
        self.summary_text_box.delete('1.0', 'end')
        self.summary_text_box.insert('1.0', text)

    def update_summary(self):
        summary_id = self.current_summary_id
        current_content = self.summary_text_box.get("1.0", "end-1c")
        self.db_thread = threading.Thread(
            target=self.db_operator.update_summary,
            args=(summary_id, current_content,),
            daemon=True
        )
        self.db_thread.start()

    # 録音関連
    def start_recording(self):
        """threadにて録音開始 """
        if self.is_recording:
            return

        self.log('録音を開始します。')
        self.is_recording = True
        self.recording_stop_event.clear()

        self.record_start_time = time.time()
        self.record_time_seconds = 0
        self.update_timer_label()
        self.start_timer()

        self.btn_record_start.configure(state='disabled',
                                        text="録音中...",
                                        )
        self.lbl_timer.configure(fg_color="#fff799")
        self.btn_record_stop.configure(state='normal')

        self.recording_thread = threading.Thread(
            target=self.recorder.recording_start,
            daemon=True)
        self.recording_thread.start()

    def stop_recording(self):
        """
        録音停止 → Gemini キューに追加
        """
        if not self.is_recording:
            return

        self.log('録音を停止しました。')
        self.is_recording = False

        self.lbl_timer.configure(text='00:00')

        # 録音スレッドに停止合図
        self.recording_stop_event.set()

        if self.recording_thread is not None:
            self.recording_thread.join()
            self.recording_thread = None

        self.btn_record_stop.configure(state='disabled')
        self.btn_record_start.configure(state='normal',
                                        text="録音(F1)",
                                        )
        self.lbl_timer.configure(fg_color="transparent")
        recorded_file = self.recorder.recording_stop() # stop_event をここで使わないなら引数無しにしてもOK

        if recorded_file.get('status') == 'success':
            file_path = recorded_file.get('file_path')
            # self.log(f'Gemini 処理キューに追加しました: {file_path}')
            self.gemini_queue.put(file_path)
        else:
            self.log(recorded_file.get('message'))

    # 録音タイマー関連
    def start_timer(self):
        """1秒ごとに録音時間を更新するループを開始"""
        # すぐに一回実行
        self.update_record_time()

    def update_record_time(self):
        """録音時間を計算してラベルに反映し、次の after を予約"""
        if not self.is_recording or self.record_start_time is None:
            return

        now = time.time()
        self.record_time_seconds = int(now - self.record_start_time)

        # ラベル更新
        self.update_timer_label()

        # 🎯 タイムアウト機能（必要なら）
        if 0 < self.max_record_seconds <= self.record_time_seconds:
            self.log("タイムアウトにより録音停止")
            self.stop_recording()
            return

        # 1秒後にまた呼ぶ
        self.record_timer_id = self.after(1000, self.update_record_time)

    def update_timer_label(self):
        """record_time_seconds を mm:ss 形式にして表示"""
        sec = self.record_time_seconds
        minutes = sec // 60
        seconds = sec % 60
        self.lbl_timer.configure(text=f"{minutes:02d}:{seconds:02d}")

    # Gemini関連
    def _gemini_worker(self):
        """Gemini 要約を順番に処理するワーカースレッド"""
        while True:
            # キューから次のファイルパスを取得（何もなければここで待機する）
            file_path = self.gemini_queue.get()

            try:
                # 実際の Gemini 呼び出し
                self.log(f'Gemini 要約を開始します。')
                self.gemini_task(file_path)
                self.log(f'Gemini 要約が完了しました。')
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                self.log(f'Gemini 要約中にエラー: {e}')
            finally:
                # キューに対して「1 個処理完了」と通知
                self.gemini_queue.task_done()

    def gemini_task(self, recorded_file):
        """録音したファイルをGeminiに投げて要約する"""
        try:
            result = self.gemini.summarize(recorded_file)

            if result.get('status') == 'success':
                summarized_json = result.get('result')
                data = json.loads(summarized_json)
                summarized_text = data.get('summary')
                summarized_text = summarized_text.replace("。", "。\n")

                summarized_transcript = data.get('transcript')

                name = str(self.selected_name)
                memo = str(self.memo_input_box.get_text())
                if memo in ('', '0'):
                    memo = None
                self.after(0, self._update_summary_text, summarized_text)

                self.db_thread = threading.Thread(
                    target=self.db_operator.save_summary,
                    args=(summarized_text, name, memo,),
                    daemon=True
                )
                self.db_thread.start()

                self.db_thread = threading.Thread(
                    target=self.db_operator.save_transcript,
                    args=(summarized_transcript, name),
                    daemon=True
                )
                self.db_thread.start()

        except Exception as e:
            self.after(0,self.log, f'要約エラー：{e}')

    # def gemini_task(self, recorded_file) -> bool:
    #     try:
    #         # もし self.gemini.client.host みたいな形でエンドポイントが取れるなら print
    #         try:
    #             host = getattr(self.gemini, "host", None)
    #             if host:
    #                 self.log(f"Gemini host = {repr(host)}")
    #         except Exception:
    #             pass
    #
    #         result = self.gemini.summarize(recorded_file)
    #
    #     except Exception as e:
    #         # ここで会社PC特有のエラー内容をログに出す
    #         self.log(f"Gemini への接続に失敗しました: {repr(e)}")
    #         return False
    #
    #     if not result or result.get('status') != 'success':
    #         self.log(f"Gemini 要約失敗: {result}")
    #         return False
    #
    #     summarized_text = result.get('summary', '')
    #     # 要約結果をUIに反映
    #     self.after(0, self._update_summary_text, summarized_text)
    #     return True

    # 自動ペースト
    def auto_paste(self):
        text = self.summary_text_box.get('1.0', 'end-1c')
        self.update_summary()
        self.log('自動ペーストしています。')
        result = self.autogui.paste(text)
        if result.get('status') == 'success':
            self.log(result.get('message'))
        else:
            self.log(f"自動ペーストエラー: {result.get('message')}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
