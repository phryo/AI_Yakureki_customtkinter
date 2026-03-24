
from google import genai
from google.genai.errors import APIError
from google.genai import types

from settings import setting


class Gemini:
    def __init__(self):
        self.client = genai.Client()
        self.prompt = setting.PROMPT

    def summarize(self, recorded_file):
        uploaded_file = None
        try:
            uploaded_file = self.client.files.upload(file=recorded_file)
            response = self.client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=[
                    self.prompt,
                    uploaded_file],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="medium"),
                )
            )
            print(response)
            summarized_text = getattr(response, 'text', None)

            if not summarized_text:
                summarized_text = self._extract_text_from_candidates(response)

            if not isinstance(summarized_text, str) or not summarized_text.strip():
                return {
                    'status': 'error',
                    'message': f"Geminiの応答が空でした。response={response!r}",
                }

            summarized_text = self.split_summarized_text(summarized_text)

            return {'status':'success',
                    'summary': summarized_text}

        except APIError as e:
            return {'status':'error',
                    'message': f'要約できませんでした。：{e}'}

        except Exception as e:
            return {"status": "error", "message": f"要約処理中に例外が発生しました：{e}"}

        finally:
            if uploaded_file:
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except Exception as e:
                    print(e)

    @staticmethod
    def _extract_text_from_candidates(response) -> str:
        """
        response.text が None のケース（候補が構造化されている/安全フィルタ等）に備え、
        candidates[].content.parts[].text を拾う。
        """
        try:
            candidates = getattr(response, "candidates", None) or []
            if not candidates:
                return ""

            content = getattr(candidates[0], "content", None)
            parts = getattr(content, "parts", None) or []
            texts = []
            for p in parts:
                t = getattr(p, "text", None)
                if isinstance(t, str) and t:
                    texts.append(t)
            return "\n".join(texts).strip()
        except Exception:
            return ""

    @staticmethod
    def split_summarized_text(text: str) ->str:
        """
        Geminiが最初に吐き出す「以下の通り出力します」等の削除する
        """
        if not text:
            return text

        index = text.find('【')
        if index == -1:
            return text
        return text[index:]
