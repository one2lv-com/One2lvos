import sys, time
import riva.client
from riva.client.proto import riva_tts_pb2, riva_asr_pb2
from common import *

h, names, key = load_keys()[0]
print("using", names[0])
# TTS voices
a = auth(key, TTS_FID)
tts = riva.client.SpeechSynthesisService(a)
try:
    cfg = tts.stub.GetRivaSynthesisConfig(riva_tts_pb2.RivaSynthesisConfigRequest(), metadata=a.get_auth_metadata())
    for m in cfg.model_config:
        p = m.parameters
        print("TTS model", m.model_name, "| lang", p.get("language_code"), "| voices:", p.get("subvoices", p.get("voice_name")))
except Exception as e:
    print("TTS cfg err", short_err(e))

for fid in sys.argv[1:]:
    a = auth(key, fid)
    asr = riva.client.ASRService(a)
    try:
        cfg = asr.stub.GetRivaSpeechRecognitionConfig(riva_asr_pb2.RivaSpeechRecognitionConfigRequest(), metadata=a.get_auth_metadata())
        for m in cfg.model_config:
            print("ASR", fid[:8], m.model_name, dict(m.parameters))
    except Exception as e:
        print("ASR cfg err", fid[:8], short_err(e))
