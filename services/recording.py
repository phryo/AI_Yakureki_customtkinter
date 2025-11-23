import threading

import numpy as np
import sounddevice as sd
import soundfile as sf

from settings.setting import SAMPLERATE, WAVE_OUTPUT_FILENAME


class Recorder:
    def __init__(self, stop_event: threading.Event):
        self.flames = None
        self.recording_stop_event = stop_event

    def callback(self, indata, frames, time, status):
        self.flames.append(indata.copy())

    def recording_start(self):
        self.flames = []
        try:
            with sd.InputStream(
                    callback=self.callback,
                    device=0):
                while not self.recording_stop_event.is_set():
                    sd.sleep(100)

        except Exception as e:
            return {'error': str(e)}

    def recording_stop(self):
        if self.flames:
            recording_data = np.concatenate(self.flames, axis=0)
            sf.write(WAVE_OUTPUT_FILENAME, recording_data, SAMPLERATE)

            return {'status': 'success',
                    'file_path': WAVE_OUTPUT_FILENAME}
        else:
            return {'status': 'error',
                    'message': 'No recording'}

