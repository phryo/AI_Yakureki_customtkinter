import time
import re
import platform
import pyperclip

import customtkinter as ctk
import pyautogui


ctk.set_appearance_mode("Light")  # 好きな方でOK

# 独自テーマをPython内に定義
LEMON_THEME = {
    "button_color": "#FFF176",      # レモンイエロー
    "button_hover": "#FFEE58",
    "frame_color": "#F5F5DC",
    "text_color": "#000000"
}

BLUE_THEME = {
    "button_color": "#1E88E5",
    "button_hover": "#1565C0",
    "frame_color": "#0D47A1",
    "text_color": "#FFFFFF"
}


class Paste:
    def __init__(self):
        self.is_pasting = False

    @staticmethod
    def split_sections(text: str) -> dict:
        """
        【見出し】ごとに文章を分割して辞書にまとめる
        key: 見出しの中身（例: "服薬状況"）
        value: そのセクションの本文
        """
        pattern = r'【(.+?)】\s*([\s\S]*?)(?=\n*【.+?】|\Z)'
        summary_dict = {}

        for m in re.finditer(pattern, text):
            title = m.group(1).strip()
            body = m.group(2).strip()
            summary_dict[title] = body

        return summary_dict

    def paste(self, mode: str):
        """クリップボードのテキストを使ってペースト"""
        text = pyperclip.paste()
        if not text.strip():
            return  # クリップボードが空なら何もしない

        summary_dict = self.split_sections(text)

        def _common_command(key, section_title):
            """コマンド入力 + 内容ペースト"""
            if section_title not in summary_dict:
                return  # セクションがなければスキップ

            pyperclip.copy(summary_dict[section_title])

            pyautogui.hotkey('shift', ';', interval=0.1)
            pyautogui.press(key)
            pyautogui.press('enter')
            time.sleep(0.3)

            if platform.system() == 'Darwin':  # macOS
                pyautogui.hotkey('command', 'v')
            else:  # Windows / Linux
                pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(0.3)

        def _screen_target():
            # 画面サイズを取得し、ターゲット位置を計算
            screen_width, screen_height = pyautogui.size()
            target_x = int(screen_width / 10)
            target_y = int(screen_height / 2 - 20)

            # マウスを指定位置に移動し、クリック
            time.sleep(0.5)
            pyautogui.moveTo(target_x, target_y)
            pyautogui.doubleClick(target_x, target_y)
            time.sleep(0.5)

        _screen_target()

        # ▼ モードに応じてコマンドだけ切り替え
        if mode == '+7/+4ペースト':
            _common_command('/', '服用状況')
            _common_command('*', '体調変化')
            _common_command('7', 'S/O（患者）')
            _common_command('4', 'A/P（指導）')
            _common_command('k', '計画')
        else:  # provisional
            _common_command('+', '服用状況')
            _common_command('+', '体調変化')
            _common_command('+', 'S/O（患者）')
            _common_command('+', 'A/P（指導）')
            _common_command('+', '計画')


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.paste = Paste()
        self.theme = LEMON_THEME  # 初期テーマ
        self.mode = '+7/+4ペースト'      # 初期モード

        self.title('ペーストアプリver1.1')
        self.geometry("400x200")
        self.attributes('-topmost', True)

        self.create_widgets()
        self.apply_theme()

    def create_widgets(self):
        self.frame = ctk.CTkFrame(self)
        self.frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.lbl_mode = ctk.CTkLabel(self.frame, text=f"モード: {self.mode}")
        self.lbl_mode.pack(pady=(0, 10))

        self.btn_paste = ctk.CTkButton(
            self.frame,
            text=self.mode,
            command=lambda: self.paste.paste(self.mode),
        )
        self.btn_paste.pack(pady=5)

        self.btn_change = ctk.CTkButton(
            self.frame,
            text="ペースト方法切り替え",
            command=self.change_mode
        )
        self.btn_change.pack(pady=5)

    def apply_theme(self):
        """現在の self.theme の色を各ウィジェットに反映"""
        t = self.theme
        self.frame.configure(fg_color=t["frame_color"])
        self.btn_paste.configure(
            fg_color=t["button_color"],
            hover_color=t["button_hover"],
            text_color=t["text_color"],
        )
        self.btn_change.configure(
            fg_color=t["button_color"],
            hover_color=t["button_hover"],
            text_color=t["text_color"],
        )
        self.lbl_mode.configure(text_color=t["text_color"])

    def change_mode(self):
        """モード & テーマ切り替え"""
        if self.mode == '+7/+4ペースト':
            self.mode = '++(仮)ペースト'
            self.theme = BLUE_THEME
        else:
            self.mode = '+7/+4ペースト'
            self.theme = LEMON_THEME

        self.lbl_mode.configure(text=f"モード: {self.mode}")
        self.btn_paste.configure(text=self.mode)
        self.apply_theme()


if __name__ == "__main__":
    app = App()
    app.mainloop()
