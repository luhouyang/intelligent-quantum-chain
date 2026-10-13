import json
import urllib.request
import urllib.error
import re
import random
from typing import Dict, Any, Tuple, Generator


class LocalQwenAgent:
    def __init__(self,
                 model_name: str = "kwangsuklee/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-GGUF:latest",
                 ollama_url: str = "http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.ollama_url = ollama_url

    def _system_prompt(self) -> str:
        return (
            "You are a strict Web3 transaction parameter extractor. "
            "First, briefly show your step-by-step reasoning inside <think> and </think> tags. "
            "Then extract parameters accurately from the user prompt into JSON ONLY.\n"
            "Rules:\n"
            "1. Extract the exact asset name (e.g., Bitcoin, ETH, USDC, BRICS_Unit).\n"
            "2. Extract the exact numerical amount.\n"
            "3. Extract the exact recipient/destination name or address.\n"
            "4. Extract the distance in km as a float if specified (e.g. '55km away' -> 55.0), else default to 15.0.\n\n"
            "Required JSON Schema:\n"
            '{"intent_id": "STRING", "asset": "STRING", "amount": FLOAT, "dest": "STRING", "distance_km": FLOAT}'
        )

    def parse_instruction_to_intent_stream(self, user_prompt: str) -> Generator[Tuple[Dict[str, Any], str], None, None]:
        """Streams raw LLM tokens chunk-by-chunk, exactly like the Gradio app terminal."""
        payload = {
            "model": self.model_name,
            "prompt": f"{self._system_prompt()}\nUser Prompt: {user_prompt}\nOutput:",
            "stream": True,
            "options": {"temperature": 0.0}
        }
        accumulated_tokens = ""
        try:
            req = urllib.request.Request(
                self.ollama_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                for line in response:
                    if line:
                        chunk_json = json.loads(line.decode('utf-8'))
                        token = chunk_json.get("response", "")
                        accumulated_tokens += token
                        yield {}, accumulated_tokens  # live raw tokens

                json_match = re.search(r'\{.*\}', accumulated_tokens, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    if "intent_id" not in parsed or not parsed["intent_id"]:
                        parsed["intent_id"] = f"INT-{random.randint(1000, 9999)}"
                    yield parsed, accumulated_tokens
                else:
                    raise ValueError(f"LLM stream completed without valid JSON.\nOutput:\n{accumulated_tokens}")
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"LLM Connection Error: Unable to reach local Ollama service at '{self.ollama_url}'. "
                f"Ensure Ollama is running (`ollama serve`) and model '{self.model_name}' is loaded. Details: {e}"
            )
        except Exception as e:
            raise RuntimeError(f"LLM Parsing Failure: {e}")

    def parse_instruction_to_intent(self, user_prompt: str) -> Tuple[Dict[str, Any], str]:
        """Non-streaming convenience wrapper over the stream."""
        intent: Dict[str, Any] = {}
        tokens = ""
        for partial_intent, stream_tokens in self.parse_instruction_to_intent_stream(user_prompt):
            if partial_intent:
                intent = partial_intent
            tokens = stream_tokens
        return intent, tokens