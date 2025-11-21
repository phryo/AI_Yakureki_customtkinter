
from google import genai
from google.genai.errors import APIError

import setting

class Gemini:
    def __init__(self):
        self.client = genai.Client()
        self.prompt = setting.PROMPT
        self.uploaded_file = None

    def summarize(self, recorded_file):
        try:
            self.uploaded_file = self.client.files.upload(file=recorded_file)
            response = self.client.models.generate_content(
                model='gemini-2.5-pro',
                contents=[
                    self.prompt,
                    self.uploaded_file]
            )
            summarized_text = response.text
            return {'status':'success',
                    'summary': summarized_text}
        except APIError as e:
            return {'status':'error',
                    'message': f'要約できませんでした。：{e}'}

        finally:
            if self.uploaded_file:
                try:
                    self.client.files.delete(name=self.uploaded_file.name)
                except Exception as e:
                    print(e)