from datetime import date
import sqlite3
from typing import Any, Optional

from services.db_oparation import DBOperator
from services.gemini import Gemini
from services.paste import AutoPaste


class MainController:
    """UI から業務ロジックを分離するコントローラ。"""

    def __init__(
        self,
        db_operator: Optional[DBOperator] = None,
        gemini: Optional[Gemini] = None,
        auto_paste: Optional[AutoPaste] = None,
    ):
        self.db_operator = db_operator or DBOperator()
        self.gemini = gemini or Gemini()
        self.auto_paste_service = auto_paste or AutoPaste()

    def load_names_list(self) -> list[str]:
        return self.db_operator.load_names_list()

    def add_name(self, name: str) -> dict[str, Any]:
        input_name = name.strip()
        if not input_name:
            return {"status": "error", "message": "登録する名前が入力されていません。"}

        self.db_operator.add_name(input_name)
        return {
            "status": "success",
            "message": f"{input_name}を追加しました。",
            "names_list": self.load_names_list(),
            "selected_name": input_name,
        }

    def delete_name(self, name: str) -> dict[str, Any]:
        input_name = name.strip()
        if not input_name:
            return {"status": "error", "message": "削除する名前が選択されていません。"}

        self.db_operator.delete_name(input_name)
        names_list = self.load_names_list()
        return {
            "status": "success",
            "message": f"{input_name}を削除しました。",
            "names_list": names_list,
            "selected_name": names_list[0] if names_list else "",
        }

    def rename_name(self, current_name: str, new_name: str) -> dict[str, Any]:
        input_current_name = current_name.strip()
        input_new_name = new_name.strip()

        if not input_current_name:
            return {"status": "error", "message": "変更する名前が選択されていません。"}
        if not input_new_name:
            return {"status": "error", "message": "変更後の名前が入力されていません。"}
        if input_current_name == input_new_name:
            return {"status": "error", "message": "変更後の名前が現在の名前と同じです。"}

        try:
            self.db_operator.rename_name(input_current_name, input_new_name)
        except sqlite3.IntegrityError:
            return {"status": "error", "message": "同じ名前が既に登録されています。"}
        except Exception as e:
            return {"status": "error", "message": f"名前変更に失敗しました。: {e}"}

        names_list = self.load_names_list()
        selected_name = input_new_name if input_new_name in names_list else (names_list[0] if names_list else "")
        return {
            "status": "success",
            "message": f"{input_current_name}を{input_new_name}に変更しました。",
            "names_list": names_list,
            "selected_name": selected_name,
        }

    def load_today_summary_titles(self) -> list[str]:
        today_str = date.today().strftime("%Y-%m-%d")
        summaries_list = self.db_operator.load_summary(today_str)
        return [
            f"{created_at[5:].replace('-', '/')} | {memo or ''}"
            for (_id, _name, memo, _content, created_at, _transcription) in summaries_list
        ]

    def load_summaries(self, target_date: Optional[str], name: Optional[str]) -> dict[str, Any]:
        lookup_date = (target_date or "").strip() or date.today().strftime("%Y-%m-%d")
        summaries_list = self.db_operator.load_summary(lookup_date, name or None)
        summaries_dict = {
            f"{created_at[5:].replace('-', '/')} | {memo or ''}": {
                "id": _id,
                "content": self._normalize_text(content),
                "transcription": self._normalize_text(transcription),
            }
            for (_id, _name, memo, content, created_at, transcription) in summaries_list
        }
        return {
            "status": "success",
            "target_date": lookup_date,
            "summaries_dict": summaries_dict,
            "dropdown_values": list(sorted(summaries_dict.keys(), reverse=True)),
        }

    def load_dictionaries(self, name: Optional[str]) -> dict[str, Any]:
        dictionaries_list = self.db_operator.load_dictionaries(name or None)
        dictionaries_dict = {
            title: {
                "id": _id,
                "title": self._normalize_text(title),
                "content": self._normalize_text(content),
            }
            for (_id, _name, title, content, _created_at) in dictionaries_list
        }
        return {
            "status": "success",
            "selected_name": name or "",
            "dictionaries_dict": dictionaries_dict,
            "dropdown_values": [row[2] for row in dictionaries_list],
        }

    @staticmethod
    def get_summary_data(summaries_dict: dict[str, dict[str, Any]], selected_label: str) -> dict[str, Any]:
        data = summaries_dict.get(selected_label)
        if not data:
            return {"status": "error", "message": "要約データが取得できませんでした。"}
        return {
            "status": "success",
            "id": data.get("id"),
            "content": data.get("content") or "",
            "transcription": data.get("transcription") or "",
        }

    @staticmethod
    def get_dictionary_data(
        dictionaries_dict: dict[str, dict[str, Any]],
        selected_label: str
    ) -> dict[str, Any]:
        data = dictionaries_dict.get(selected_label)
        if not data:
            return {"status": "error", "message": "辞書データが取得できませんでした。"}
        return {
            "status": "success",
            "id": data.get("id"),
            "title": data.get("title") or "",
            "content": data.get("content") or "",
        }

    def create_dictionary(self, name: str, title: str, content: str) -> dict[str, Any]:
        input_name = (name or "").strip()
        input_title = self._normalize_text(title)
        input_content = str(content) if content is not None else ""

        if not input_name:
            return {"status": "error", "message": "辞書を登録する名前が選択されていません。"}
        if not input_title:
            return {"status": "error", "message": "辞書タイトルを入力してください。"}
        if self.db_operator.dictionary_title_exists(input_name, input_title):
            return {"status": "error", "message": "同じタイトルの辞書が既に登録されています。"}

        try:
            dictionary_id = self.db_operator.save_dictionary(input_name, input_title, input_content)
        except sqlite3.IntegrityError:
            return {"status": "error", "message": "同じタイトルの辞書が既に登録されています。"}

        return {
            "status": "success",
            "message": f"辞書「{input_title}」を登録しました。",
            "dictionary_id": dictionary_id,
            "selected_label": input_title,
        }

    def overwrite_dictionary(self, dictionary_id: int, name: str, title: str, content: str) -> dict[str, Any]:
        input_name = (name or "").strip()
        input_title = self._normalize_text(title)
        input_content = str(content) if content is not None else ""

        if not input_name:
            return {"status": "error", "message": "辞書を保存する名前が選択されていません。"}
        if not dictionary_id:
            return {"status": "error", "message": "更新対象の辞書が選択されていません。"}
        if not input_title:
            return {"status": "error", "message": "辞書タイトルを入力してください。"}
        if self.db_operator.dictionary_title_exists(input_name, input_title, exclude_id=dictionary_id):
            return {"status": "error", "message": "同じタイトルの辞書が既に登録されています。"}

        try:
            self.db_operator.overwrite_save_dictionary(dictionary_id, input_name, input_title, input_content)
        except sqlite3.IntegrityError:
            return {"status": "error", "message": "同じタイトルの辞書が既に登録されています。"}

        return {
            "status": "success",
            "message": f"辞書「{input_title}」を上書き保存しました。",
            "dictionary_id": dictionary_id,
            "selected_label": input_title,
        }

    def delete_dictionary(self, dictionary_id: int, title: str) -> dict[str, Any]:
        if not dictionary_id:
            return {"status": "error", "message": "削除対象の辞書が選択されていません。"}

        self.db_operator.delete_dictionary(dictionary_id)
        return {
            "status": "success",
            "message": f"辞書「{self._normalize_text(title)}」を削除しました。",
        }

    def copy_text(self, text: str) -> dict[str, Any]:
        return self.auto_paste_service.copy_text(text)

    @staticmethod
    def _normalize_memo(memo: Any) -> Optional[str]:
        text = str(memo).strip() if memo is not None else ""
        if text in ("", "0"):
            return None
        return text

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return str(value).strip() if value is not None else ""

    @staticmethod
    def _missing_summary_headers(summary_text: str) -> list[str]:
        required_headers = [
            "【服薬状況】",
            "【副作用】",
            "【S/O（患者）】",
            "【A/P（指導）】",
            "【計画】",
        ]
        return [header for header in required_headers if header not in summary_text]

    @staticmethod
    def _separate_summary_and_transcription(text: str) -> tuple[str, str]:
        summary_headers = (
            "【服薬状況】",
            "【副作用】",
            "【S/O（患者）】",
            "【A/P（指導）】",
            "【計画】",
        )
        indices = [text.find(header) for header in summary_headers if text.find(header) != -1]
        if not indices:
            return "", text.strip()

        index = min(indices)
        return text[:index].strip(), text[index:].strip()


    def summarize_and_save(self, recorded_file: str, name: str, memo: Any) -> dict[str, Any]:
        result = self.gemini.summarize(recorded_file)
        if result.get("status") != "success":
            return {
                "status": "error",
                "message": result.get("message", "要約に失敗しました。"),
            }

        result_text = self._normalize_text(result.get("summary", ""))
        transcription, summary = self._separate_summary_and_transcription(result_text)
        summarized_text = self._normalize_text(summary).replace("。", "。\n")
        transcription_text = self._normalize_text(transcription)

        missing_headers = self._missing_summary_headers(summarized_text)
        if missing_headers:
            joined_headers = "、".join(missing_headers)
            return {
                "status": "error",
                "message": f"要約の形式が不正です。次の見出しが不足しています: {joined_headers}",
            }

        summary_id = self.db_operator.save_summary(
            summarized_text,
            str(name),
            self._normalize_memo(memo),
            transcription_text
        )
        return {
            "status": "success",
            "summary": summarized_text,
            "transcription": transcription_text,
            "summary_id": summary_id,
        }

    def overwrite_summary(self, summary_id: int, content: str) -> None:
        self.db_operator.overwrite_save_summary(summary_id, content)

    def auto_paste(self, text: str) -> dict[str, Any]:
        return self.auto_paste_service.paste(text)
