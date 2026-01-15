import datetime
import tkinter as tk

import customtkinter as ctk


import tkinter as tk
import customtkinter as ctk


class NumberEntry(ctk.CTkFrame):
    def __init__(
        self,
        master,
        min_value=None,
        max_value=None,
        step=1,
        placeholder_text: str = "",
        entry_width: int = 80,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.min_value = min_value
        self.max_value = max_value
        self.step = step

        # 入力値（文字列として保持）
        self.var = tk.StringVar(value="")

        # エントリ本体（バリデーションは付けない → 何でも入る）
        self.entry = ctk.CTkEntry(
            self,
            textvariable=self.var,
            justify="right",
            width=entry_width,
            placeholder_text=placeholder_text,
        )
        self.entry.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 2))

        # ▲ボタン
        self.btn_up = ctk.CTkButton(
            self, text="▲", width=24, height=16,
            command=self.increment
        )
        self.btn_up.grid(row=0, column=1, sticky="ew")

        # ▼ボタン
        self.btn_down = ctk.CTkButton(
            self, text="▼", width=24, height=16,
            command=self.decrement
        )
        self.btn_down.grid(row=1, column=1, sticky="ew")

        self.grid_rowconfigure((0, 1), weight=1)
        self.grid_columnconfigure(0, weight=1)

    # ===== 公開メソッド =====

    def get(self) -> int:
        """
        数値として取得。
        - 空文字: 0 を返す
        - 数値に変換できない文字列: 0 を返す
        """
        text = self.var.get().strip()
        if text == "":
            return 0
        try:
            return int(text)
        except ValueError:
            return 0

    def get_text(self) -> str:
        """生の文字列をそのまま取得"""
        return self.var.get()

    def set(self, value):
        """文字列でも数値でもセット可能"""
        self.var.set(str(value))

    # ===== 内部ヘルパ =====

    def _current_int_or_none(self):
        """
        現在の値を int に変換。
        - 空文字: 0 を返す
        - 変換できない: None を返す
        """
        text = self.var.get().strip()
        if text == "":
            return 0  # 空は 0 とみなす
        try:
            return int(text)
        except ValueError:
            return None

    # ===== ▲▼ボタン =====

    def increment(self):
        cur = self._current_int_or_none()
        if cur is None:
            # 数値に変換できない場合は何もしない
            return

        value = cur + self.step

        if self.max_value is not None:
            value = min(value, self.max_value)
        if self.min_value is not None:
            value = max(value, self.min_value)

        self.set(value)

    def decrement(self):
        cur = self._current_int_or_none()
        if cur is None:
            # 数値に変換できない場合は何もしない
            return

        value = cur - self.step

        if self.max_value is not None:
            value = min(value, self.max_value)
        if self.min_value is not None:
            value = max(value, self.min_value)

        self.set(value)


class DateSelector(ctk.CTkFrame):
    """
    ・左右の矢印ボタンで日付を移動
    ・📅ボタンで「直近7日だけ出るカレンダー風ポップアップ」
    ・今日を基準に retention_days 日前までしか選択できない
    """
    def __init__(self, master, retention_days: int = 7, command=None, **kwargs):
        super().__init__(master, **kwargs)

        self.command = command          # 日付変更時に呼びたいコールバック（任意）
        self.retention_days = retention_days

        # 日付の範囲（今日〜 retention_days-1 日前まで）
        self.max_date = datetime.date.today()
        self.min_date = self.max_date - datetime.timedelta(days=retention_days - 1)
        self.selected_date = self.max_date

        # 左右ボタン
        self.btn_prev = ctk.CTkButton(self, text="◀", width=32, command=self.prev_day)
        self.btn_prev.grid(row=0, column=0, padx=(0, 4))

        # 日付表示ラベル
        self.lbl_date = ctk.CTkLabel(self, text="", width=140, anchor="center")
        self.lbl_date.grid(row=0, column=1, padx=4)

        # カレンダー（7日分の一覧）ボタン
        # self.btn_calendar = ctk.CTkButton(self, text="📅", width=32, command=self.open_popup)
        # self.btn_calendar.grid(row=0, column=2, padx=(4, 0))

        # 次の日へボタン
        self.btn_next = ctk.CTkButton(self, text="▶", width=32, command=self.next_day)
        self.btn_next.grid(row=0, column=2, padx=(4, 0))

        self.grid_columnconfigure(1, weight=1)

        self._update_ui(initial=True)

    # 公開メソッド：date型で取得
    def get_date(self) -> datetime.date:
        return self.selected_date

    # 公開メソッド：文字列で取得
    def get_date_str(self, fmt: str = "%Y-%m-%d") -> str:
        return self.selected_date.strftime(fmt)

    # 公開メソッド：外から日付をセット（範囲外なら補正）
    def set_date(self, date_obj: datetime.date):
        if date_obj < self.min_date:
            date_obj = self.min_date
        elif date_obj > self.max_date:
            date_obj = self.max_date
        self.selected_date = date_obj
        self._update_ui()

    # 前日へ
    def prev_day(self):
        new_date = self.selected_date - datetime.timedelta(days=1)
        if new_date >= self.min_date:
            self.selected_date = new_date
            self._update_ui()

    # 翌日へ
    def next_day(self):
        new_date = self.selected_date + datetime.timedelta(days=1)
        if new_date <= self.max_date:
            self.selected_date = new_date
            self._update_ui()

    # 日付表示の更新＆ボタンの有効／無効制御
    def _update_ui(self, initial=False):
        self.lbl_date.configure(text=self._format_date(self.selected_date))

        # 範囲外に行けないようにボタン状態を制御
        if self.selected_date <= self.min_date:
            self.btn_prev.configure(state="disabled")
        else:
            self.btn_prev.configure(state="normal")

        if self.selected_date >= self.max_date:
            self.btn_next.configure(state="disabled")
        else:
            self.btn_next.configure(state="normal")

        # 初期表示以外ならコールバック呼び出し
        if (not initial) and self.command is not None:
            self.command(self.selected_date)

    # 「YYYY-MM-DD(曜)」形式に整形
    def _format_date(self, d: datetime.date) -> str:
        weekdays = "月火水木金土日"
        return d.strftime(f"%Y-%m-%d（{weekdays[d.weekday()]}）")

    # 7日分だけ出る簡易カレンダー（ポップアップ）
    def open_popup(self):
        top = ctk.CTkToplevel(self)
        top.title("日付を選択")
        top.resizable(False, False)
        top.grab_set()   # モーダルっぽく

        # 新しい順（今日が一番上）に並べる
        for i in range(self.retention_days):
            d = self.max_date - datetime.timedelta(days=i)
            btn = ctk.CTkButton(
                top,
                text=self._format_date(d),
                command=lambda dd=d, win=top: self._select_from_popup(dd, win),
                width=200
            )
            btn.grid(row=i, column=0, padx=10, pady=4, sticky="ew")

    # ポップアップから日付を選択したとき
    def _select_from_popup(self, date_obj: datetime.date, window):
        self.selected_date = date_obj
        self._update_ui()
        window.destroy()

class CenteredDropdown(ctk.CTkFrame):
    """
    ・選択中の項目をボタン位置付近に表示するカスタムドロップダウン
    ・最大 max_rows 行ぶんの高さで、超えたらスクロール
    ・背景：白／文字：黒
    """

    def __init__(self, master, values=None, width=160,
                 command=None, max_rows=9, **kwargs):
        super().__init__(master, **kwargs)

        self.values = list(values) if values is not None else []
        self.command = command
        self.width = width
        self.dynamic_resizing = False
        self.max_rows = max_rows

        initial = self.values[0] if self.values else ""
        self.var = tk.StringVar(value=initial)

        # 本体ボタン（選択中を表示）
        self.button = ctk.CTkButton(
            self,
            textvariable=self.var,
            width=self.width,
            anchor="w",
            fg_color="white",
            text_color="black",
            hover_color="#eeeeee",
            command=self._open_popup,
        )
        self.button.grid(row=0, column=0, sticky="ew")
        self.grid_columnconfigure(0, weight=1)

        self._popup = None

    # ========= 公開 API =========

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str):
        if value in self.values:
            self.var.set(value)
            if self.command:
                self.command(value)

    def configure_values(self, values):
        self.values = list(values)
        if self.values and self.var.get() not in self.values:
            self.var.set(self.values[0])

    # CTkComboBox 互換っぽく configure(values=..., command=...) を使えるように
    def configure(self, **kwargs):
        if "values" in kwargs:
            self.configure_values(kwargs.pop("values"))
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        return super().configure(**kwargs)

    def cget(self, key):
        if key == "values":
            return self.values
        if key == "command":
            return self.command
        return super().cget(key)

    # ========= 内部処理 =========

    def _open_popup(self):
        if not self.values:
            return

        # 既に開いていたら閉じる
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.destroy()

        top = ctk.CTkToplevel(self)
        self._popup = top
        top.overrideredirect(True)       # 枠なし
        top.attributes("-topmost", True)
        top.configure(fg_color="white")  # 背景白

        # スクロール可能フレーム
        frame = ctk.CTkScrollableFrame(
            top,
            width=self.width,
            fg_color="white",
            border_width=1,
            border_color="gray70",
        )
        frame.grid(row=0, column=0, sticky="nsew")
        top.grid_rowconfigure(0, weight=1)
        top.grid_columnconfigure(0, weight=1)

        current_value = self.var.get()
        try:
            current_index = self.values.index(current_value)
        except ValueError:
            current_index = 0

        # ボタン群を追加（全件）
        for i, value in enumerate(self.values):
            is_current = (i == current_index)
            btn = ctk.CTkButton(
                frame,
                text=value,
                width=self.width,
                anchor="w",
                fg_color=("#cce7ff" if is_current else "white"),  # 選択中だけ薄い水色
                text_color="black",
                hover_color="#eeeeee",
                corner_radius=0,
                command=lambda v=value: self._on_select(v),
            )
            btn.grid(row=i, column=0, sticky="ew")

        # レイアウト確定して高さを取得
        top.update_idletasks()

        children = frame.winfo_children()
        if children:
            item_height = children[0].winfo_height()
        else:
            item_height = self.winfo_height() or 24

        # 1行の高さから「中身として見せたい高さ」を計算
        visible_rows = min(self.max_rows, len(self.values))
        inner_height = item_height * visible_rows  # ← 中身（行ぶん）の高さ

        # 上下の余白・枠ぶんちょっと足す
        extra_padding = 7  # ここを増やすと上下の余裕が増える
        visible_height = inner_height + extra_padding

        # ポップアップの位置（選択中の行がボタンの位置付近になるように）
        btn_x = self.winfo_rootx()
        btn_y = self.winfo_rooty()

        popup_y = btn_y - int(visible_height // 2) + int(item_height // 2)
        if popup_y < 0:
            popup_y = 0

        # 幅 x 高さ + 位置
        top.geometry(f"{self.width}x{int(visible_height)}+{btn_x}+{popup_y}")
        top.update_idletasks()

        # スクロール位置調整：選択中が中央付近に来るように
        total_height = item_height * len(self.values)
        if total_height > inner_height:
            canvas = frame._parent_canvas  # CTkScrollableFrame の内部キャンバス
            center_y = item_height * current_index + item_height / 2
            first_visible_y = center_y - inner_height / 2
            fraction = max(0, min(1, first_visible_y / (total_height - inner_height)))
            canvas.yview_moveto(fraction)

        # フォーカス／外クリックで閉じる
        top.focus_force()
        top.bind("<FocusOut>", lambda e: self._safe_destroy())
        top.bind("<Escape>", lambda e: self._safe_destroy())

    def _on_select(self, value: str):
        self.var.set(value)
        self._safe_destroy()
        if self.command:
            self.command(value)

    def _safe_destroy(self):
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None
