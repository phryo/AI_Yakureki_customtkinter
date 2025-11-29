import os
from datetime import date
import threading
import tkinter
import queue

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
        self.names_list.insert(0, '')

        self.summaries_dict = {}

        # ウィジェット（上から順番）
        self.btn_record_start = None
        self.btn_record_stop = None
        self.name_dropdown_label = None
        self.name_dropdown = None
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
        self.flame_pharmacists = ctk.CTkFrame(self)
        self.flame_pharmacists.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # 名前のドロップダウン
        self.name_dropdown_label = ctk.CTkLabel(self.flame_pharmacists, text="投薬者")
        self.name_dropdown_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")
        self.name_dropdown = ctk.CTkComboBox(self.flame_pharmacists, values=self.names_list)
        self.name_dropdown.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")

        # 名前新規追加
        self.btn_add_name = ctk.CTkButton(
            self.flame_pharmacists,
            text='投薬者登録',
            command=lambda: self.add_name(self.name_dropdown.get()),
            width=80, height=28,
        )
        self.btn_add_name.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # 名前削除
        self.btn_delete_name = ctk.CTkButton(
            self.flame_pharmacists,
            text='投薬者削除',
            command=lambda: self.delete_name(self.name_dropdown.get()),
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

        self.dropdown_summary = settings.widgets.CenteredDropdown(
            self.flame_load_summaries,
            values=summaries_title_list,
            command=self.on_selected_summary
        )
        self.dropdown_summary.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_load_summaries = ctk.CTkButton(
            self.flame_load_summaries,
            width=200, height=30,
            text='要約の読み込み（日付、名前指定）',
            command=self.load_summaries_list
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
        self.name_dropdown.configure(values=names_list)
        self.name_dropdown.set(name)

    def delete_name(self, name: str):
        """投薬者の削除"""
        name = name.strip()
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
        names_list = self.db_operator.load_names_list()
        names_list.insert(0, '')
        self.name_dropdown.configure(values=names_list)

        if len(names_list) > 1:
            self.name_dropdown.set(names_list[1])
        else:
            self.name_dropdown.set('')

    def load_summaries_list(self):
        """要約のリストをDBから読み込む"""
        # 例： '2025-11-23' という文字列が入っている
        target_date = self.date_selector.get_date_str().strip()
        name = self.name_dropdown.get()

        if target_date:
            summaries_list = self.db_operator.load_summary(target_date, name)
        else:
            today_str = date.today().strftime('%Y-%m-%d')
            summaries_list = self.db_operator.load_summary(today_str, name)

        self.summaries_dict = {
            f"{created_at[5:].replace('-', '/')} / {memo or ''}": content
            for (_id, _name, memo, content, created_at) in summaries_list
        }

        # ドロップダウン表示用に整形
        dropdown_values = list(sorted(self.summaries_dict.keys()))

        self.log(f'{target_date} / {name}の要約を読み込みました。')
        self.dropdown_summary.configure_values(dropdown_values)

    def on_selected_summary(self, selected_label: str):
        """ドロップダウンで要約を選択したときに呼ばれる"""
        content = self.summaries_dict.get(selected_label, "")

        self.summary_text_box.delete("1.0", "end")
        self.summary_text_box.insert("end", content)

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

        # 録音スレッドに停止合図
        self.recording_stop_event.set()

        if self.recording_thread is not None:
            self.recording_thread.join()
            self.recording_thread = None

        self.btn_record_stop.configure(state='disabled')
        self.btn_record_start.configure(state='normal')

        recorded_file = self.recorder.recording_stop() # stop_event をここで使わないなら引数無しにしてもOK

        if recorded_file.get('status') == 'success':
            file_path = recorded_file.get('file_path')
            # self.log(f'Gemini 処理キューに追加しました: {file_path}')
            self.gemini_queue.put(file_path)
        else:
            self.log(recorded_file.get('message'))

    def _update_summary_text(self, text: str):
        """要約結果をテキストボックスに反映（メインスレッドで実行）"""
        self.summary_text_box.delete('1.0', 'end')
        self.summary_text_box.insert('1.0', text)

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
                summarized_text = result.get('summary')
                name = str(self.name_dropdown.get())
                memo = str(self.memo_input_box.get())
                if memo in ('', '0'):
                    memo = None
                self.after(0, self._update_summary_text, summarized_text)

                self.db_thread = threading.Thread(
                    target=self.db_operator.save_summary,
                    args=(summarized_text, name, memo,),
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
