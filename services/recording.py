
import numpy as np
import sounddevice as sd
import soundfile as sf

from setting import SAMPLERATE, WAVE_OUTPUT_FILENAME


class Recorder:
    def __init__(self):
        self.flames = []
        self.recorded_file = None

    def callback(self, data, frames, time, status):
        self.flames.append(data.copy())

    def recording_start(self, stop_event):
        self.flames = []
        try:
            with sd.InputStream(
                    callback=self.callback,
                    device=0):
                while not stop_event.is_set():
                    sd.sleep(100)

        except Exception as e:
            return {'error': str(e)}

    def recording_stop(self, stop_event):
        stop_event.set()
        if self.flames:
            recording_data = np.concatenate(self.flames, axis=0)
            sf.write(WAVE_OUTPUT_FILENAME, recording_data, SAMPLERATE)

            return {'status': 'success',
                    'file_path': WAVE_OUTPUT_FILENAME}
        else:
            return {'status': 'error',
                    'message': 'No recording'}

