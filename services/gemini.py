from google import genai
from google.genai import types
from google.genai.errors import APIError

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
                model='gemini-2.5-flash',
                contents=[
                    self.prompt,
                    uploaded_file],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            summarized_text = response.text
            return {'status':'success',
                    'result': summarized_text}
        except APIError as e:
            return {'status':'error',
                    'message': f'要約できませんでした。：{e}'}

        finally:
            if uploaded_file:
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except Exception as e:
                    print(e)