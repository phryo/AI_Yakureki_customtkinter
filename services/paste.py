import platform
import pygetwindow as gw
import pyperclip
import re
import time

import pyautogui

from settings.setting import SECTION_MAPPING


class PasteCancelledException(Exception):
    """ペーストがキャンセルされたことを示すためのカスタム例外"""
    pass

class AutoGui:
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

    def paste(self, text):
        if not text:
            return {'status': 'error', 'message': 'ペーストする内容がありません。'}
        self.is_pasting = True

        def _screen_target():
            if not self.is_pasting:
                raise PasteCancelledException

            # 調剤システムを最前面にアクティブ化
            windows = gw.getWindowsWithTitle('調剤システム')
            if windows:
                win = windows[0]
                win.activate()
            else:
                raise Exception

            # 画面サイズを取得し、ターゲット位置を計算
            screen_width, screen_height = pyautogui.size()
            target_x = int(screen_width / 10)
            target_y = int(screen_height / 2 - 20)

            # マウスを指定位置に移動し、クリック
            time.sleep(0.5)
            pyautogui.moveTo(target_x, target_y)
            pyautogui.doubleClick(target_x, target_y)
            time.sleep(0.5)

        def _common_command(key, section_title):
            """コマンド入力　+　内容ペースト"""
            if not self.is_pasting:  # 実行前に必ず中断チェック
                raise PasteCancelledException

            pyautogui.hotkey('shift', ';', interval=0.1)
            time.sleep(0.3)
            pyautogui.press(key)
            pyautogui.press('enter')
            time.sleep(0.3)

            if section_title not in summary_dict:
                raise ValueError(f'「{section_title}」が見つかりません。')
            pyperclip.copy(summary_dict[section_title])

            if platform.system() == 'Darwin':  # macOS
                pyautogui.hotkey('command', 'v')
            else:  # Windows / Linux
                pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(0.3)

        try:
            summary_dict = self.split_sections(text)
            _screen_target()
            for key, section_title in SECTION_MAPPING:
                _common_command(key, section_title)

            return {'status': 'success', 'message': '自動ペーストが完了しました。'}

        except PasteCancelledException:
            return {'status': 'error', 'message': 'ペーストを中断しました。'}

        except Exception as e:
            return {'status': 'error', 'message': f'エラー：{e}'}

        finally:
            self.is_pasting = False

    def cancel(self):
        """外部からペースト処理を中断する"""
        self.is_pasting = False
