import datetime
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
        # Frame 側の初期化
        super().__init__(master, **kwargs)

        self.min_value = min_value
        self.max_value = max_value
        self.step = step

        # 最初は空にしておく（デフォルト何も入らない）
        self.var = tk.StringVar(value="")

        # --------- エントリー本体 ---------
        self.entry = ctk.CTkEntry(
            self,
            textvariable=self.var,
            justify="right",
            width=entry_width,
            placeholder_text=placeholder_text,  # ★ ここで渡す
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

        # 数字以外が入らないよう簡易バリデーション
        vcmd = (self.register(self._validate), "%P")
        self.entry.configure(validate="key", validatecommand=vcmd)

    # 値を取得（空なら 0 扱いにする例）
    def get(self) -> int:
        text = self.var.get().strip()
        if text == "":
            return 0  # or None にしたければここを変更
        try:
            return int(text)
        except ValueError:
            return 0

    # 値をセット
    def set(self, value: int):
        self.var.set(str(value))

    def increment(self):
        value = self.get() + self.step
        if self.max_value is not None:
            value = min(value, self.max_value)
        self.set(value)

    def decrement(self):
        value = self.get() - self.step
        if self.min_value is not None:
            value = max(value, self.min_value)
        self.set(value)

    # 入力チェック（空文字はOK、数字だけ許可）
    def _validate(self, new_value: str):
        if new_value == "":
            return True
        return new_value.isdigit()

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
