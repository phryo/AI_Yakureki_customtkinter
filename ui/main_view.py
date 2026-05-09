import os
import queue
import re
import threading
import time
import tkinter

import customtkinter as ctk

from controller.main_controller import MainController
from services.recording import Recorder
import settings.setting
import ui.widgets


class App(ctk.CTk):
    VIEW_MODE_SUMMARY = "要約モード"
    VIEW_MODE_DICTIONARY = "辞書登録モード"

    def __init__(self):
        """アプリ本体を初期化する。"""
        super().__init__()

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.controller = MainController()
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

        # ★ Gemini 用キュー & ワーカースレッド
        self.gemini_queue = queue.Queue()
        self.gemini_worker_thread = threading.Thread(
            target=self._gemini_worker,
            daemon=True
        )
        self.gemini_worker_thread.start()

        self.is_gemini_available = self.controller.is_gemini_available()
        self.gemini_disabled_reason = self.controller.get_gemini_disabled_reason()

        self.title("Gemini　AI薬歴")
        self.geometry("600x1000")
        # self.attributes('-topmost', True)

        # ★ ウィンドウ全体の grid 設定
        # 横方向：col=0 を伸ばす（ただし中身のwidgetはstickyで制御）
        self.grid_columnconfigure(0, weight=1)
        # 縦方向：row=4（summaryのフレーム）だけ伸ばす
        self.grid_rowconfigure(4, weight=1)

        # 辞書、リスト
        self.names_list = self.controller.load_names_list()

        # 選択中の投薬者
        self.selected_name = self.names_list[0] if self.names_list else ""

        self.summaries_dict = {}
        self.summary_dropdown_values: list[str] = []
        self.current_summary_label = ""

        self.current_summary_id = None
        self.current_summary_content = ""
        self.current_summary_transcription = ""

        self.dictionaries_dict = {}
        self.dictionary_dropdown_values: list[str] = []
        self.current_dictionary_label = ""
        self.current_dictionary_id = None
        self.current_dictionary_title = ""
        self.current_dictionary_content = ""

        self.current_view_mode = self.VIEW_MODE_SUMMARY

        # ウィジェット（上から順番）
        self.btn_record_start = None
        self.btn_record_stop = None
        self.lbl_timer = None
        self.name_button_frame = None
        self.name_buttons: dict[str, ctk.CTkButton] = {}
        self.name_entry = None
        self.btn_add_name = None
        self.btn_rename_name = None
        self.btn_delete_name = None
        self.date_selector = None
        self.memo_label = None
        self.memo_input_box = None
        self.dropdown_summary = None
        self.dropdown_summary_display_mode = None
        self.btn_load_summaries = None
        self.summary_label = None
        self.summary_section_frame = None
        self.summary_section_widgets: dict[str, ctk.CTkTextbox] = {}
        self.btn_section_copy: dict[str, ctk.CTkButton] = {}
        self.dictionary_title_frame = None
        self.dictionary_title_label = None
        self.dictionary_title_entry = None
        self.dictionary_content_text_box = None
        self.btn_paste = None
        self.dropdown_change_paste_speed = None
        self.btn_create_dictionary = None
        self.btn_delete_dictionary_item = None
        self.btn_update_summary = None
        self.log_label = None
        self.log_box = None

        self.create_widgets()
        self._apply_recording_availability()

    def create_widgets(self):
        """画面全体のUIを構築する。"""
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
        self.name_button_frame.grid(row=1, column=0, columnspan=4, padx=10, pady=(0, 5), sticky="we")
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

        # 名前変更
        self.btn_rename_name = ctk.CTkButton(
            self.frame_pharmacists,
            text="投薬者名変更",
            command=self.rename_selected_name,
            width=100, height=28,
        )
        self.btn_rename_name.grid(row=2, column=2, padx=5, pady=(0, 5), sticky="w")

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
        self.btn_delete_name.grid(row=2, column=3, padx=5, pady=(0, 5), sticky="w")


        # ===== メモ =====
        self.frame_memo = ctk.CTkFrame(self)
        self.frame_memo.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.frame_memo.grid_columnconfigure(1, weight=1)

        self.date_selector = ui.widgets.DateSelector(
            self.frame_memo,
            retention_days=7,
        )
        self.date_selector.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="w")

        self.memo_label = ctk.CTkLabel(self.frame_memo, text="メモ：")
        self.memo_label.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")

        self.memo_input_box = ui.widgets.NumberEntry(
            self.frame_memo,
            placeholder_text="メモ",
            min_value=0,
            max_value=500,
            step=1
        )
        self.memo_input_box.grid(row=1, column=1, padx=(0, 10), pady=5, sticky="w")


        # ===要約再読み込み===
        summaries_title_list = self.controller.load_today_summary_titles()
        self.summary_dropdown_values = summaries_title_list[:]

        self.frame_load_summaries = ctk.CTkFrame(self)
        self.frame_load_summaries.grid(row=3, column=0, padx=5, pady=5, sticky="w")

        self.dropdown_summary = ui.widgets.CenteredDropdown(
            self.frame_load_summaries,
            values=summaries_title_list,
            command=self.on_selected_summary
        )
        self.dropdown_summary.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_load_summaries = ctk.CTkButton(
            self.frame_load_summaries,
            width=200, height=30,
            text="要約の読み込み（日付、名前指定）",
            command=self.load_current_mode_items
        )
        self.btn_load_summaries.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.dropdown_summary_display_mode = ctk.CTkComboBox(
            self.frame_load_summaries,
            values=[self.VIEW_MODE_SUMMARY, self.VIEW_MODE_DICTIONARY],
            command=self.on_view_mode_changed,
            width=100,
        )
        self.dropdown_summary_display_mode.grid(row=0, column=2, padx=5, pady=5, sticky="w")


        # ===== 要約（ここだけリサイズ対象） =====
        self.frame_summary = ctk.CTkFrame(self)
        self.frame_summary.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")
        self.frame_summary.grid_columnconfigure(0, weight=1)  # 横方向
        self.frame_summary.grid_rowconfigure(1, weight=1)

        self.dictionary_title_frame = ctk.CTkFrame(
            self.frame_summary,
            fg_color="transparent",
            border_width=0,
        )
        self.dictionary_title_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.dictionary_title_frame.grid_columnconfigure(1, weight=1)

        self.dictionary_title_label = ctk.CTkLabel(self.dictionary_title_frame, text="タイトル：")
        self.dictionary_title_label.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="w")

        self.dictionary_title_entry = ctk.CTkEntry(
            self.dictionary_title_frame,
            placeholder_text="辞書タイトル",
        )
        self.dictionary_title_entry.grid(row=0, column=1, padx=0, pady=0, sticky="ew")

        self.summary_section_frame = ctk.CTkScrollableFrame(
            self.frame_summary,
            fg_color="transparent",
            border_width=0,
        )
        self.summary_section_frame.grid(row=1, column=0, padx=5, pady=3, sticky="nsew")
        self.summary_section_frame.grid_columnconfigure(1, weight=1)

        section_heights = {
            "服薬状況": 50,
            "副作用": 50,
            "計画": 36,
        }
        default_section_height = 100
        for row_index, (_, section_title) in enumerate(settings.setting.SECTION_MAPPING):
            section_label = ctk.CTkLabel(
                self.summary_section_frame,
                text=section_title,
                width=50
            )
            section_label.grid(row=row_index * 2, column=0, padx=0, pady=0, sticky="ew")

            btn_section_copy = ctk.CTkButton(
                self.summary_section_frame,
                text="コピー",
                height=18,
                width=40,
                command=lambda: self._read_a_summary_section_from_widget(section_title)
            )
            btn_section_copy.grid(row=row_index * 2 + 1, column=0, padx=5, pady=0, sticky="new")
            self.btn_section_copy[section_title] = btn_section_copy

            section_text_box = ctk.CTkTextbox(
                self.summary_section_frame,
                height=section_heights.get(section_title, default_section_height),
            )
            section_text_box.grid(row=row_index * 2, column=1, padx=5, pady=5, rowspan=2, sticky="ew")
            self.summary_section_widgets[section_title] = section_text_box
            self.summary_section_widgets[section_title]._textbox.bind("<Tab>", self.on_tab_key_down)

        self.dictionary_content_text_box = ctk.CTkTextbox(self.frame_summary, height=150)
        self.dictionary_content_text_box.grid(row=1, column=0, padx=10, pady=(0, 0), sticky="nsew")

        self.frame_btn_in_summary = ctk.CTkFrame(self.frame_summary,
                                                 fg_color="transparent",
                                                 border_width=0,)
        self.frame_btn_in_summary.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        # 自動ペーストボタン
        self.btn_paste = ctk.CTkButton(
            self.frame_btn_in_summary,
            text="自動ペースト",
            width=120,
            command=self.auto_paste
        )
        self.btn_paste.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # ペースト速度変更
        label_change_paste_speed = ctk.CTkLabel(
            self.frame_btn_in_summary,
            text="速度調整:"
        )
        label_change_paste_speed.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.dropdown_change_paste_speed = ui.widgets.CenteredDropdown(
            self.frame_btn_in_summary,
            values=["x" + str(round(i*0.1, 1)) for i in range(10, 0, -1)],
            width=60
        )
        self.dropdown_change_paste_speed.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.dropdown_change_paste_speed.set("1.0")

        self.btn_create_dictionary = ctk.CTkButton(
            self.frame_btn_in_summary,
            text="新規登録",
            width=80,
            command=self.create_dictionary
        )
        self.btn_create_dictionary.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.btn_delete_dictionary_item = ctk.CTkButton(
            self.frame_btn_in_summary,
            text="削除",
            width=60,
            fg_color="transparent",
            border_color="#666666",
            border_width=1,
            text_color="#444444",
            hover_color="#DDDDDD",
            command=self.delete_dictionary
        )
        self.btn_delete_dictionary_item.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # 要約保存ボタン
        self.btn_update_summary = ctk.CTkButton(
            self.frame_btn_in_summary,
            text="保存",
            width=50,
            command=self.overwrite_save_summary
        )
        self.btn_update_summary.grid(row=0, column=3, padx=5, pady=5, sticky="w")


        # ===== ログ =====
        self.frame_log = ctk.CTkFrame(self)
        self.frame_log.grid(row=5, column=0, padx=5, pady=5, sticky="ew")
        self.frame_log.grid_columnconfigure(0, weight=1)

        self.log_label = ctk.CTkLabel(self.frame_log, text="ログ：")
        self.log_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.log_box = ctk.CTkTextbox(self.frame_log, height=70)
        self.log_box.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        self._sync_current_view_mode()

    def _apply_recording_availability(self):
        """録音機能の利用可否をUIに反映する。"""
        if self.is_gemini_available:
            return

        self.btn_record_start.configure(state="disabled")
        self.btn_record_stop.configure(state="disabled")
        self.log(self.gemini_disabled_reason)

    def _can_use_recording(self) -> bool:
        """録音機能を利用できるか返す。"""
        if self.is_gemini_available:
            return True

        return False


    # ====== 関数 ======
    def on_f1(self, event=None):
        """F1キー入力で録音状態を切り替える。"""
        if not self._can_use_recording():
            return
        self.toggle_recording()

    def on_tab_key_down(self, event):
        """tabキーでsummary_sectionを切り替える"""
        focus_widget_list = [section for _, section in settings.setting.SECTION_MAPPING]
        focused = self.focus_get()
        focused_key = None
        for key in focus_widget_list:
            widget = self.summary_section_widgets[key]
            if focused == widget._textbox:
                focused_key = key
                break

        if focused_key is None:
            return "break"

        try:
            current_index = focus_widget_list.index(focused_key)
            next_key = focus_widget_list[current_index + 1]
            self.summary_section_widgets[next_key]._textbox.focus_set()
            return "break"
        except IndexError:
            next_key = focus_widget_list[0]
            self.summary_section_widgets[next_key]._textbox.focus_set()
            return "break"


    def toggle_recording(self):
        """録音の開始と停止を切り替える。"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    # ログ表示
    def log(self, text: str):
        """ログ欄にメッセージを表示する。"""
        self.log_box.insert("1.0", f'{text}\n')
        self.log_box.update()

    # 投薬者関連
    def render_name_buttons(self):
        """投薬者ボタンを再描画する。"""
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
        """投薬者を選択し、必要なら辞書一覧を更新する。"""
        self.selected_name = name
        self.update_name_button_styles()
        if self.current_view_mode == self.VIEW_MODE_DICTIONARY:
            self.load_dictionaries_list()

    def update_name_button_styles(self):
        """選択中の投薬者ボタンの見た目を更新する。"""
        for name, btn in self.name_buttons.items():
            if name == self.selected_name:
                btn.configure(fg_color="#1f6aa5", text_color="white", border_width=0)
            else:
                btn.configure(fg_color="transparent", border_color="#666666", border_width=1, text_color="#444444")

    def add_name(self):
        """投薬者を追加する。"""
        result = self.controller.add_name(self.name_entry.get())
        if result.get("status") != "success":
            self.log(result.get("message"))
            return

        self.log(result.get("message"))
        self.names_list = result.get("names_list", [])
        self.selected_name = result.get("selected_name", "")
        self.name_entry.delete(0, "end")
        self.render_name_buttons()
        self._refresh_current_mode_after_name_change()

    def delete_name(self):
        """投薬者を削除する。"""
        name = self.name_entry.get().strip() or self.selected_name
        if not name:
            self.log("削除する名前が選択されていません。")
            return
        possible_delete = tkinter.messagebox.askokcancel(
            '確認',
            '本当に削除してもよろしいですか？'
        )
        if not possible_delete:
            return
        result = self.controller.delete_name(name)
        if result.get("status") != "success":
            self.log(result.get("message"))
            return
        self.log(result.get("message"))
        self.names_list = result.get("names_list", [])
        self.selected_name = result.get("selected_name", "")
        self.render_name_buttons()
        self._refresh_current_mode_after_name_change()

    def rename_selected_name(self):
        """選択中の投薬者名を変更する。"""
        current_name = (self.selected_name or "").strip()
        new_name = self.name_entry.get().strip()

        if not current_name:
            self.log("変更する名前が選択されていません。")
            return
        if not new_name:
            self.log("変更後の名前が入力されていません。")
            return
        if current_name == new_name:
            self.log("変更後の名前が現在の名前と同じです。")
            return

        possible_rename = tkinter.messagebox.askokcancel(
            "確認",
            f"「{current_name}」を「{new_name}」に変更しますか？"
        )
        if not possible_rename:
            return

        result = self.controller.rename_name(current_name, new_name)
        if result.get("status") != "success":
            self.log(result.get("message"))
            return

        self.log(result.get("message"))
        self.names_list = result.get("names_list", [])
        self.selected_name = result.get("selected_name", "")
        self.name_entry.delete(0, "end")
        self.render_name_buttons()
        self._refresh_current_mode_after_name_change()

    def _refresh_current_mode_after_name_change(self):
        """投薬者変更後に現在モードの内容を更新する。"""
        if self.current_view_mode == self.VIEW_MODE_DICTIONARY:
            self.load_dictionaries_list()

    # 要約・辞書関連
    def load_current_mode_items(self):
        """現在の表示モードに対応する一覧を読み込む。"""
        if self.current_view_mode == self.VIEW_MODE_DICTIONARY:
            self.load_dictionaries_list()
        else:
            self.load_summaries_list()

    def load_summaries_list(self):
        """要約一覧を読み込む。"""
        target_date = self.date_selector.get_date_str().strip()
        name = self.selected_name

        result = self.controller.load_summaries(target_date, name)
        self.summaries_dict = result.get("summaries_dict", {})
        self.summary_dropdown_values = result.get("dropdown_values", [])
        self._apply_current_summary_selection()
        self.log(f"{result.get('target_date')} | {name}の要約を読み込みました。")

    def load_dictionaries_list(self, preferred_label: str | None = None):
        """選択中の投薬者の辞書一覧を読み込む。"""
        name = self.selected_name
        result = self.controller.load_dictionaries(name)
        self.dictionaries_dict = result.get("dictionaries_dict", {})
        self.dictionary_dropdown_values = result.get("dropdown_values", [])
        if preferred_label is not None:
            self.current_dictionary_label = preferred_label
        self._apply_current_dictionary_selection()
        self.log(f"{name}の辞書を読み込みました。")

    def on_selected_summary(self, selected_label: str):
        """選択中の要約または辞書内容を表示する。"""
        if self.current_view_mode == self.VIEW_MODE_DICTIONARY:
            result = self.controller.get_dictionary_data(self.dictionaries_dict, selected_label)
            if result.get("status") != "success":
                self.log(result.get("message"))
                return

            self.current_dictionary_label = selected_label
            self._set_current_dictionary_data(
                dictionary_id=result.get("id"),
                title=result.get("title", ""),
                content=result.get("content", ""),
            )
            self._render_current_view_text()
            return

        result = self.controller.get_summary_data(self.summaries_dict, selected_label)
        if result.get("status") != "success":
            self.log(result.get("message"))
            return

        self.current_summary_label = selected_label
        self._set_current_summary_data(
            summary_id=result.get("id"),
            content=result.get("content", ""),
            transcription=result.get("transcription", ""),
        )
        self._render_current_view_text()

    def _build_empty_summary_sections(self) -> dict[str, str]:
        """要約5項目の空データを返す。"""
        return {
            section_title: ""
            for _, section_title in settings.setting.SECTION_MAPPING
        }

    def _split_summary_content(self, text: str) -> dict[str, str]:
        """見出し付き要約文字列を5項目辞書へ分割する。"""
        sections = self._build_empty_summary_sections()
        if not text:
            return sections

        pattern = r"【(.+?)】\s*([\s\S]*?)(?=\n*【.+?】|\Z)"
        for match in re.finditer(pattern, text):
            section_title = match.group(1).strip()
            if section_title not in sections:
                continue
            sections[section_title] = match.group(2).strip()
        return sections

    def _join_summary_sections(self, sections: dict[str, str]) -> str:
        """5項目辞書を既存互換の見出し付き要約文字列へ再結合する。"""
        parts = []
        for _, section_title in settings.setting.SECTION_MAPPING:
            body = (sections.get(section_title) or "").strip()
            parts.append(f"【{section_title}】\n{body}")
        return "\n\n".join(parts)

    def _read_a_summary_section_from_widget(self, section_title: str) -> str:
        text_box = self.summary_section_widgets[section_title]
        self.log(f"{section_title} をコピーしました")
        return text_box.get("1.0", "end-1c").strip()

    def _read_summary_sections_from_widgets(self) -> dict[str, str]:
        """5個の要約textboxから内容を取得する。"""
        sections = self._build_empty_summary_sections()
        for section_title, text_box in self.summary_section_widgets.items():
            sections[section_title] = text_box.get("1.0", "end-1c").strip()
        return sections

    def _write_summary_sections_to_widgets(self, sections: dict[str, str]):
        """5個の要約textboxへ内容を書き込む。"""
        normalized_sections = self._build_empty_summary_sections()
        normalized_sections.update(sections or {})
        for _, section_title in settings.setting.SECTION_MAPPING:
            text_box = self.summary_section_widgets[section_title]
            text_box.delete("1.0", "end")
            text_box.insert("1.0", normalized_sections.get(section_title, ""))

    def _read_summary_text(self) -> str:
        """要約textbox群の内容を既存互換文字列として取得する。"""
        return self._join_summary_sections(self._read_summary_sections_from_widgets())

    def _read_dictionary_title(self) -> str:
        """辞書タイトル欄の内容を取得する。"""
        return self.dictionary_title_entry.get().strip()

    def _write_dictionary_title(self, text: str):
        """辞書タイトル欄へ内容を書き込む。"""
        self.dictionary_title_entry.delete(0, "end")
        self.dictionary_title_entry.insert(0, text or "")

    def _read_dictionary_content_text_box(self) -> str:
        """辞書本文欄の内容を取得する。"""
        return self.dictionary_content_text_box.get("1.0", "end-1c")

    def _write_dictionary_content_text_box(self, text: str):
        """辞書本文欄へ内容を書き込む。"""
        self.dictionary_content_text_box.delete("1.0", "end")
        self.dictionary_content_text_box.insert("1.0", text or "")

    def _set_current_summary_data(self, summary_id: int | None, content: str, transcription: str):
        """現在の要約データを保持する。"""
        self.current_summary_id = summary_id
        self.current_summary_content = content or ""
        self.current_summary_transcription = transcription or ""

    def _clear_current_summary_data(self):
        """現在の要約データをクリアする。"""
        self.current_summary_label = ""
        self._set_current_summary_data(summary_id=None, content="", transcription="")

    def _set_current_dictionary_data(self, dictionary_id: int | None, title: str, content: str):
        """現在の辞書データを保持する。"""
        self.current_dictionary_id = dictionary_id
        self.current_dictionary_title = title or ""
        self.current_dictionary_content = content or ""

    def _clear_current_dictionary_data(self):
        """現在の辞書データをクリアする。"""
        self.current_dictionary_label = ""
        self._set_current_dictionary_data(dictionary_id=None, title="", content="")

    def _sync_view_mode_dropdown(self):
        """表示モードのドロップダウンを同期する。"""
        if self.dropdown_summary_display_mode is None:
            return
        self.dropdown_summary_display_mode.set(self.current_view_mode)

    def _set_dropdown_selection(self, values: list[str], selected_label: str):
        """ドロップダウンの候補と選択値を設定する。"""
        self.dropdown_summary.configure_values(values)
        if selected_label and selected_label in values:
            self.dropdown_summary.var.set(selected_label)
        elif values:
            self.dropdown_summary.var.set(values[0])
        else:
            self.dropdown_summary.var.set("")

    def _render_current_view_text(self):
        """現在モードに応じた本文を画面へ反映する。"""
        if self.current_view_mode == self.VIEW_MODE_DICTIONARY:
            self._write_dictionary_title(self.current_dictionary_title)
            self._write_dictionary_content_text_box(self.current_dictionary_content)
        else:
            self._write_summary_sections_to_widgets(
                self._split_summary_content(self.current_summary_content)
            )

    def _sync_current_view_mode(self):
        """現在の表示モードに合わせてUIを切り替える。"""
        is_dictionary_mode = self.current_view_mode == self.VIEW_MODE_DICTIONARY
        self._sync_view_mode_dropdown()
        self.btn_load_summaries.configure(
            text="辞書の読み込み（名前指定）" if is_dictionary_mode else "要約の読み込み（日付、名前指定）"
        )
        self.btn_paste.configure(
            text="全コピー" if is_dictionary_mode else "自動ペースト",
            state="normal"
        )
        self.btn_update_summary.configure(state="normal")

        if is_dictionary_mode:
            self.dictionary_title_frame.grid()
            self.dictionary_content_text_box.grid()
            self.summary_section_frame.grid_remove()
            self.dropdown_change_paste_speed.grid_remove()
            self.btn_create_dictionary.grid()
            self.btn_delete_dictionary_item.grid()
        else:
            self.dictionary_title_frame.grid_remove()
            self.dictionary_content_text_box.grid_remove()
            self.summary_section_frame.grid()
            self.btn_create_dictionary.grid_remove()
            self.btn_delete_dictionary_item.grid_remove()
            self.dropdown_change_paste_speed.grid()

        values = self.dictionary_dropdown_values if is_dictionary_mode else self.summary_dropdown_values
        selected_label = self.current_dictionary_label if is_dictionary_mode else self.current_summary_label
        self._set_dropdown_selection(values, selected_label)
        self._render_current_view_text()

    def _switch_view_mode(self, mode: str, should_reload: bool = True):
        """表示モードを切り替え、必要なら一覧を再読み込みする。"""
        normalized_mode = (
            mode if mode in (self.VIEW_MODE_SUMMARY, self.VIEW_MODE_DICTIONARY)
            else self.VIEW_MODE_SUMMARY
        )
        self.current_view_mode = normalized_mode
        self._sync_current_view_mode()
        if should_reload and self.current_view_mode == self.VIEW_MODE_DICTIONARY:
            self.load_dictionaries_list()
            return

    def on_view_mode_changed(self, selected_mode: str):
        """表示モード変更時の処理を行う。"""
        self._switch_view_mode(selected_mode, should_reload=True)

    def _apply_summary_result(self, summarized_text: str, summary_id: int, transcription: str):
        """要約結果を画面と状態に反映する。"""
        self.current_summary_label = ""
        self._set_current_summary_data(
            summary_id=summary_id,
            content=summarized_text,
            transcription=transcription,
        )
        self._switch_view_mode(self.VIEW_MODE_SUMMARY, should_reload=False)

    def _set_summary_text_box_state(self, state: str):
        """要約テキスト欄の状態を変更する。"""
        for text_box in self.summary_section_widgets.values():
            text_box.configure(state=state)

    def _apply_current_summary_selection(self):
        """現在の要約選択状態を画面へ適用する。"""
        selected_label = self.current_summary_label if self.current_summary_label in self.summary_dropdown_values else ""
        if not selected_label and self.summary_dropdown_values:
            selected_label = self.summary_dropdown_values[0]
        if selected_label:
            self.on_selected_summary(selected_label)
            self._set_dropdown_selection(self.summary_dropdown_values, selected_label)
            return
        self._clear_current_summary_data()
        if self.current_view_mode == self.VIEW_MODE_SUMMARY:
            self._sync_current_view_mode()

    def _apply_current_dictionary_selection(self):
        """現在の辞書選択状態を画面へ適用する。"""
        selected_label = self.current_dictionary_label if self.current_dictionary_label in self.dictionary_dropdown_values else ""
        if not selected_label and self.dictionary_dropdown_values:
            selected_label = self.dictionary_dropdown_values[0]
        if selected_label:
            self.on_selected_summary(selected_label)
            self._set_dropdown_selection(self.dictionary_dropdown_values, selected_label)
            return
        self._clear_current_dictionary_data()
        if self.current_view_mode == self.VIEW_MODE_DICTIONARY:
            self._sync_current_view_mode()

    def _save_summary_without_log(self) -> bool:
        """要約を保存し、成否を返す。"""
        summary_id = self.current_summary_id
        if not summary_id:
            self.log('更新対象の要約が選択されていません。')
            return False
        current_content = self._read_summary_text()
        self.current_summary_content = current_content
        self.db_thread = threading.Thread(
            target=self.controller.overwrite_summary,
            args=(summary_id, current_content,),
            daemon=True
        )
        self.db_thread.start()
        return True

    def _save_dictionary_without_log(self) -> bool:
        """辞書を保存し、成否を返す。"""
        dictionary_id = self.current_dictionary_id
        title = self._read_dictionary_title()
        content = self._read_dictionary_content_text_box()

        result = self.controller.overwrite_dictionary(
            dictionary_id or 0,
            self.selected_name,
            title,
            content,
        )
        if result.get("status") != "success":
            self.log(result.get("message"))
            return False

        self.current_dictionary_label = result.get("selected_label", "")
        self.load_dictionaries_list(preferred_label=self.current_dictionary_label)
        return True

    def overwrite_save_summary(self):
        """現在モードの内容を保存する。"""
        if self.current_view_mode == self.VIEW_MODE_DICTIONARY:
            if self._save_dictionary_without_log():
                self.log('辞書を上書き保存しました。')
            return

        if self._save_summary_without_log():
            self.log('上書き保存しました。')

    def create_dictionary(self):
        """新しい辞書を登録する。"""
        result = self.controller.create_dictionary(
            self.selected_name,
            self._read_dictionary_title(),
            self._read_dictionary_content_text_box(),
        )
        if result.get("status") != "success":
            self.log(result.get("message"))
            return

        self.current_dictionary_label = result.get("selected_label", "")
        self.load_dictionaries_list(preferred_label=self.current_dictionary_label)
        self.log(result.get("message"))

    def delete_dictionary(self):
        """選択中の辞書を削除する。"""
        dictionary_id = self.current_dictionary_id
        title = self.current_dictionary_title or self._read_dictionary_title()
        if not dictionary_id:
            self.log("削除対象の辞書が選択されていません。")
            return

        possible_delete = tkinter.messagebox.askokcancel(
            "確認",
            f"辞書「{title}」を削除してもよろしいですか？"
        )
        if not possible_delete:
            return

        result = self.controller.delete_dictionary(dictionary_id, title)
        if result.get("status") != "success":
            self.log(result.get("message"))
            return

        self.current_dictionary_label = ""
        self.load_dictionaries_list(preferred_label="")
        self.log(result.get("message"))

    # 録音関連
    def start_recording(self):
        """録音を開始する。"""
        if not self._can_use_recording():
            return

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
        """録音を停止し、Gemini処理へ渡す。"""
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
        """録音タイマーの更新を開始する。"""
        # すぐに一回実行
        self.update_record_time()

    def update_record_time(self):
        """録音時間を更新し、次回更新を予約する。"""
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
        """録音時間表示を更新する。"""
        sec = self.record_time_seconds
        minutes = sec // 60
        seconds = sec % 60
        self.lbl_timer.configure(text=f"{minutes:02d}:{seconds:02d}")

    # Gemini関連
    def _gemini_worker(self):
        """Gemini要約キューを順番に処理する。"""
        while True:
            # キューから次のファイルパスを取得（何もなければここで待機する）
            file_path = self.gemini_queue.get()

            try:
                # 実際の Gemini 呼び出し
                self.after(0, self.log, "Gemini 要約を開始します。")
                self.gemini_task(file_path)
                self.after(0, self.log, "Gemini 要約が完了しました。")
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                self.after(0, self.log, f"Gemini 要約中にエラー: {e}")
            finally:
                # キューに対して「1 個処理完了」と通知
                self.gemini_queue.task_done()

    def gemini_task(self, recorded_file):
        """録音ファイルをGeminiで要約する。"""
        try:
            result = self.controller.summarize_and_save(
                recorded_file,
                self.selected_name,
                self.memo_input_box.get_text(),
            )
            if result.get("status") == "success":
                self.after(
                    0,
                    self._apply_summary_result,
                    result.get("summary", ""),
                    result.get("summary_id"),
                    result.get("transcription", ""),
                )
            else:
                self.after(0, self.log, result.get("message", "要約に失敗しました。"))

        except Exception as e:
            self.after(0, self.log, f"要約エラー：{e}")
        finally:
            self.after(0, self._set_summary_text_box_state, "normal")


    # 自動ペースト
    def auto_paste(self):
        """現在モードに応じてコピーまたは自動ペーストを行う。"""
        if self.current_view_mode == self.VIEW_MODE_DICTIONARY:
            result = self.controller.copy_text(self._read_dictionary_content_text_box())
            if result.get('status') == 'success':
                self.log(result.get('message'))
            else:
                self.log(f"コピーエラー: {result.get('message')}")
            return
        if not self._save_summary_without_log():
            return
        text = self.current_summary_content
        self.log('自動ペーストしています。')
        paste_speed = float(self.dropdown_change_paste_speed.get()[1:])
        result = self.controller.auto_paste(text, paste_speed=paste_speed)
        if result.get('status') == 'success':
            self.log(result.get('message'))
        else:
            self.log(f"自動ペーストエラー: {result.get('message')}")
