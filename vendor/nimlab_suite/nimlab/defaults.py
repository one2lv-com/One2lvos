"""Built-in starting data, used when a file is missing.

ROUTING and CANDIDATE_ROUTES seed data/endpoints.json on a fresh install (they
are the v3.0 registry and route matrix). STARTER_CLUSTER and STARTER_PROMPTS
are written as config_cluster.json / config_system_prompts.json when those
files are absent, so a fresh unzip starts with working roles and prompts.
"""

ROUTING = {'version': '2026.1',
 'gateways': {'integrate': 'https://integrate.api.nvidia.com/v1',
              'ai_api': 'https://ai.api.nvidia.com/v1',
              'nvcf_functions': 'https://api.nvcf.nvidia.com/v2/nvcf/functions',
              'nvcf_grpc': 'grpc.nvcf.nvidia.com:443'},
 'static_routes': {'chat': {'gateway': 'integrate', 'path': '/chat/completions', 'method': 'POST'},
                   'chat_stream': {'gateway': 'integrate', 'path': '/chat/completions', 'method': 'POST'},
                   'vision': {'gateway': 'integrate', 'path': '/chat/completions', 'method': 'POST'},
                   'completions': {'gateway': 'integrate', 'path': '/completions', 'method': 'POST'},
                   'embeddings': {'gateway': 'integrate', 'path': '/embeddings', 'method': 'POST'},
                   'embeddings_typed': {'gateway': 'integrate', 'path': '/embeddings', 'method': 'POST'},
                   'ranking': {'gateway': 'integrate', 'path': '/ranking', 'method': 'POST'},
                   'responses': {'gateway': 'integrate', 'path': '/responses', 'method': 'POST'},
                   'models': {'gateway': 'integrate', 'path': '/models', 'method': 'GET'},
                   'rerank_classic': {'gateway': 'ai_api',
                                      'path': '/retrieval/nvidia/reranking',
                                      'method': 'POST'},
                   'embeddings_retrieval': {'gateway': 'ai_api',
                                            'path': '/retrieval/nvidia/embeddings',
                                            'method': 'POST'}},
 'explicit_model_overrides': {'nvidia/magpie-tts-zeroshot': {'gateway': 'ai_api',
                                                             'path': '/cv/nvidia/magpie-tts-zeroshot',
                                                             'method': 'POST',
                                                             'kind': 'audio_tts'},
                              'nvidia/magpie-tts-multilingual': {'gateway': 'ai_api',
                                                                 'path': '/cv/nvidia/magpie-tts-multilingual',
                                                                 'method': 'POST',
                                                                 'kind': 'audio_tts'}},
 'dynamic_prefix_rules': [{'pattern': 'cosmos', 'gateway': 'ai_api', 'prefix': '/cosmos', 'kind': 'video'},
                          {'pattern': 'genai',
                           'gateway': 'ai_api',
                           'prefix': '/genai',
                           'kind': 'image_gen',
                           'keywords': ['flux', 'stable-diffusion', 'sdxl', 'imagen', 'sana']},
                          {'pattern': 'retrieval',
                           'gateway': 'ai_api',
                           'prefix': '/retrieval',
                           'kind': 'document',
                           'keywords': ['docling', 'parse', 'ocr', 'nemoretriever']},
                          {'pattern': 'cv',
                           'gateway': 'ai_api',
                           'prefix': '/cv',
                           'kind': 'vision_task',
                           'keywords': ['segment', 'detect', 'depth', 'pose']}],
 'nvcf_fallbacks': ['parakeet', 'canary', 'riva', 'fastpitch', 'hifigan', 'chatterbox']}

CANDIDATE_ROUTES = [{'name': 'integrate_chat_completions',
  'url': 'https://integrate.api.nvidia.com/v1/chat/completions',
  'kind': 'chat',
  'method': 'POST'},
 {'name': 'integrate_vision_chat',
  'url': 'https://integrate.api.nvidia.com/v1/chat/completions',
  'kind': 'vision',
  'method': 'POST'},
 {'name': 'integrate_embeddings',
  'url': 'https://integrate.api.nvidia.com/v1/embeddings',
  'kind': 'embeddings',
  'method': 'POST'},
 {'name': 'integrate_embeddings_typed',
  'url': 'https://integrate.api.nvidia.com/v1/embeddings',
  'kind': 'embeddings_typed',
  'method': 'POST'},
 {'name': 'integrate_ranking',
  'url': 'https://integrate.api.nvidia.com/v1/ranking',
  'kind': 'ranking',
  'method': 'POST'},
 {'name': 'integrate_completions',
  'url': 'https://integrate.api.nvidia.com/v1/completions',
  'kind': 'completions',
  'method': 'POST'},
 {'name': 'integrate_responses',
  'url': 'https://integrate.api.nvidia.com/v1/responses',
  'kind': 'responses',
  'method': 'POST'},
 {'name': 'ai_api_retrieval_reranking',
  'url': 'https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking',
  'kind': 'rerank',
  'method': 'POST'},
 {'name': 'ai_api_retrieval_embeddings',
  'url': 'https://ai.api.nvidia.com/v1/retrieval/nvidia/embeddings',
  'kind': 'embeddings_retrieval',
  'method': 'POST'},
 {'name': 'ai_api_cv_model_path',
  'template': 'https://ai.api.nvidia.com/v1/cv/{publisher}/{name}',
  'kind': 'audio_tts',
  'method': 'POST'},
 {'name': 'ai_api_genai_model_path',
  'template': 'https://ai.api.nvidia.com/v1/genai/{publisher}/{name}',
  'kind': 'image_gen',
  'method': 'POST'},
 {'name': 'ai_api_cosmos_model_path',
  'template': 'https://ai.api.nvidia.com/v1/cosmos/{publisher}/{name}',
  'kind': 'video',
  'method': 'POST'},
 {'name': 'ai_api_retrieval_model_path',
  'template': 'https://ai.api.nvidia.com/v1/retrieval/{publisher}/{name}',
  'kind': 'document',
  'method': 'POST'}]

MATRIX_DESCRIPTION = 'Master REST endpoint candidate matrix for NVIDIA NIM and AI API probing'

STARTER_ROLE_MODELS = {
    'intent_router': 'nvidia/nemotron-3.5-bolt-e4b',
    'persona': 'poolside/laguna-xs-2.1',
    'reasoning': 'mistralai/mistral-large-4-1t-a52b',
    'coding': 'google/gemma-4-31b-it',
    'vision': 'nvidia/nemotron-3.5-super-vl-120b-a12b',
    'ocr': 'nvidia/nemotron-parse-2.0',
    'chart_parser': None,
    'video': None,
    'asr': None,
    'omni_audio': None,
    'tts': 'nvidia/magpie-tts-multilingual',
    'image_gen': None,
    'audio_gen': None,
    'embedding': 'nvidia/llama-nemotron-embed-vl-1b-v2',
    'reranker': None,
    'guard_translate': None,
}


def _starter_roles():
    from .roles import label
    out = {k: {'label': label(k), 'backend': 'model', 'model': m} for k, m in STARTER_ROLE_MODELS.items()}
    out['compactor'] = 'nvidia/nemotron-3.5-bolt-e4b'
    return out


STARTER_CLUSTER = {'roles': _starter_roles(),
 'http_settings': {'timeout_sec': 60, 'retries': 2, 'backoff_sec': 1.5},
 'voice_settings': {'voice_name': 'Magpie-Multilingual.EN-US.Aria',
                    'auto_tts': True,
                    'language': 'en-US',
                    'tts_url': 'https://877104f7-e885-42b9-8de8-f6e4c6303969.invocation.api.nvcf.nvidia.com/v1/audio/synthesize',
                    'voice_profiles': ['Magpie-Multilingual.EN-US.Aria', 'Magpie-Multilingual.EN-US.Jason']},
 'mcp_settings': {'enabled': True,
                  'url': 'https://svn-dev.online/mcp',
                  'auth': {'style': 'x-api-key', 'header_name': 'X-API-Key', 'key_env': 'MCP_API_KEY'},
                  'protocol_version': '2025-06-18',
                  'allowed_tools': [],
                  'confirm_tool_calls': True,
                  'max_tool_steps': 4,
                  'max_calls_per_step': 3,
                  'tool_timeout_sec': 20,
                  'max_result_chars': 8000,
                  'max_response_bytes': 1000000},
 'memory_settings': {'recall_top_k': 3, 'similarity_threshold': 0.45, 'rerank_candidates': 10},
 'guard_settings': {'check_input': False, 'check_output': False, 'block_on_unsafe': True,
                    'translate_target': 'English'},
 'routing_settings': {'use_intent_router': True, 'show_route': True},
 'judge_settings': {'judges': ['mistralai/mistral-large-4-1t-a52b', 'nvidia/nemotron-3-ultra-550b-a55b'],
                    'repeats': 1,
                    'judge_temperature': 0.0,
                    'max_candidates_per_type': 16,
                    'execute_generated_code': True,
                    'code_timeout_sec': 10,
                    'entity_combos': [{'name': 'current', 'roles': {}},
                                      {'name': 'ultra_brain',
                                       'roles': {'persona': 'nvidia/nemotron-3-ultra-550b-a55b'}},
                                      {'name': 'mistral_brain',
                                       'roles': {'persona': 'mistralai/mistral-large-4-1t-a52b'}}],
                    'candidate_overrides': {}},
 'discovery_settings': {'page_ttl_hours': 72,
                        'spec_ttl_hours': 72,
                        'probe_workers': 3,
                        'probe_timeout_sec': 20,
                        'host_delays_sec': {'build.nvidia.com': 10,
                                            'docs.api.nvidia.com': 3,
                                            'api.ngc.nvidia.com': 1},
                        'include_retired_in_sweep': False,
                        'playground_uses_catalog': True}}

STARTER_PROMPTS = {
    'intent_router': 'You are the intent router. Read the user turn and answer with exactly one label from the '
                     'list you are given, nothing else.',
    'persona': 'You are the primary conversational persona. Parse intent cleanly, address the user in the '
               'established persona, synthesize data from sub-models, and trigger tool calls when data must '
               'be fetched or acted upon.',
    'reasoning': 'You are the deep analytical reasoning core. Break down complex architectural and '
                 'algorithmic problems step-by-step with zero hand-waving.',
    'coding': 'You are the specialized systems programmer and tool caller. Write clean, complete, '
              'dependency-minimal code without truncation or placeholders, and call tools precisely.',
    'vision': 'You are the forensic visual analyzer. Extract exact object locations, text, dimensions, and '
              'anomalies from the provided image.',
    'ocr': 'You are the document parsing engine. Transcribe layout, data tables, and structured text '
           'verbatim without summary.',
    'chart_parser': 'You are the chart and plot parser. Read the chart type, axes, units, series and every data '
                    'point, and return them as a table, then one line on the trend.',
    'video': 'You are the video and temporal analyst. Describe what happens over time, in order, with '
             'timestamps where you can.',
    'asr': 'Transcribe the audio verbatim.',
    'omni_audio': 'You are the audio analyst. Describe music (genre, tempo, key, instruments, mood) and '
                  'ambient sound (sources, setting, events) precisely.',
    'tts': '',
    'image_gen': '',
    'audio_gen': '',
    'embedding': '',
    'reranker': '',
    'guard_translate': 'You are the translation and safety model. Translate faithfully when asked to translate; '
                       'when asked to check safety, answer SAFE or UNSAFE and a short reason.',
    'compactor': 'You are the episodic memory compactor. Compress chat turns and operational logs into '
                 'high-density semantic bullets while preserving proper nouns, exact numbers, and state '
                 'decisions.',
}
