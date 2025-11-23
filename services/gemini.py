
from google import genai
from google.genai.errors import APIError

from settings import setting


class Gemini:
    def __init__(self):
        self.client = genai.Client()
        self.prompt = setting.PROMPT
        uploaded_file = None

    def summarize(self, recorded_file):
        try:
            uploaded_file = self.client.files.upload(file=recorded_file)
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    self.prompt,
                    uploaded_file]
            )
            summarized_text = response.text
            return {'status':'success',
                    'summary': summarized_text}
        except APIError as e:
            return {'status':'error',
                    'message': f'要約できませんでした。：{e}'}

        finally:
            if uploaded_file:
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except Exception as e:
                    print(e)