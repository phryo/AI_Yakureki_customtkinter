import pyperclip
import re
import time

import pyautogui


class PasteCancelledException(Exception):
    """ペーストがキャンセルされたことを示すためのカスタム例外"""
    pass

class AutoGui:
    def __init__(self):
        self.is_running = False


    def paste(self, text):
        if not text:
            return {'status': 'error', 'message': 'ペーストする内容がありません。'}
        self.is_pasting = True

        try:
            text_list = re.split(r'【(.*?)】', text)
            command_dict = {}
            for i in range(1, len(text_list), 2):
                command_dict[text_list[i].strip()] = text_list[i + 1].strip()

            def common_command(key, command):
                # 実行前に必ず中断チェック
                if not self.is_pasting:
                    raise PasteCancelledException

                pyautogui.hotkey('shift', ';', interval=0.1)
                pyautogui.press(key)
                pyautogui.press('enter')
                time.sleep(0.3)

                pyperclip.copy(command_dict[command])
                pyautogui.hotkey('command', 'v')
                print(command_dict[command])
                time.sleep(0.3)
                pyautogui.press('enter')
                time.sleep(0.3)

            # pyautoguiによる自動操作

            # 画面サイズを取得し、ターゲット位置を計算
            if not self.is_pasting:
                raise PasteCancelledException

            screen_width, screen_height = pyautogui.size()
            target_x = int(screen_width / 10)
            target_y = int(screen_height / 2 - 20)
            print(f"ターゲット位置に移動: X={target_x}, Y={target_y}")

            # マウスを指定位置に移動し、クリック
            time.sleep(0.5)
            pyautogui.moveTo(target_x, target_y)
            pyautogui.doubleClick(target_x, target_y)
            time.sleep(0.5)

            # コマンドシーケンスを順次実行（各ステップで中断チェック）
            if not self.is_pasting:
                raise PasteCancelledException

            common_command('/', '服用状況')
            common_command('*', '副作用')
            common_command('7', '患者情報')
            common_command('4', '指導')
            common_command('k', '計画')

            self.is_pasting = False
            return {'status': 'error', 'message': '正常完了'}

        except PasteCancelledException:
            self.is_pasting = False
            return {'status': 'error', 'message': 'ペーストを中断しました。'}

        except Exception as e:
            self.is_pasting = False
            return {'status': 'error', 'message': f'エラー：{e}'}


