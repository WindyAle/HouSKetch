# model.py

import ollama
import sys

class ModelManager:
    """
    Ollama 서버와의 모든 통신을 관리하는 클래스입니다.
    연결 확인, 모델(EEVE, Chat) 준비, 임베딩 생성을 담당합니다.
    """
    def __init__(self, embedding_model='EEVE', chat_model='llama3'):
        print("Initializing ModelManager...")
        self.embedding_model = embedding_model
        self.chat_model = chat_model # Step 3 (피드백)에서 사용
        self.is_ready = False
        self._initialize_ollama()

    def _initialize_ollama(self):
        """
        Ollama 서버에 연결하고 필요한 모델이 있는지 확인합니다.
        없으면 모델을 pull 합니다.
        """
        try:
            ollama.list()
            print("Ollama connection successful.")
            
            # 필요한 모델 목록
            required_models_name = [self.embedding_model, self.chat_model]
            model_list = ollama.list()['models']
            available_models = [model['model'] for model in model_list]

            for model_name in required_models_name:
                # 모델 이름에 특수문자를 포함할 수 있으므로 startswith로 검사
                if not any(m.startswith(model_name) for m in available_models):
                    print(f"Model '{model_name}' not found. Pulling model...")
                    ollama.pull(model_name)
                    print(f"Model '{model_name}' pulled successfully.")
                else:
                    print(f"Model '{model_name}' is available.")
            
            self.is_ready = True
            self.embedding_model = model_list[0]['model']

        except Exception as e:
            print(f"Ollama connection failed. Is 'ollama serve' running?")
            print(f"Error: {e}", file=sys.stderr)
            self.is_ready = False

    def get_embedding(self, text: str) -> list[float]:
        """
        주어진 텍스트를 EEVE를 사용해 의미 벡터로 변환합니다.
        """
        if not self.is_ready or not text:
            return []
            
        try:
            response = ollama.embeddings(model=self.embedding_model, prompt=text)
            return response['embedding']
        except Exception as e:
            print(f"Error getting embedding: {e}", file=sys.stderr)
            return []
            
    # Step 3에서 상세 피드백을 생성하기 위해 미리 만들어 둡니다.
    def get_chat_response(self, system_prompt: str, user_prompt: str) -> str:
        """
        채팅 모델을 사용해 자연어 응답을 생성합니다.
        """
        if not self.is_ready:
            return "Model is not ready."
            
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
            response = ollama.chat(model=self.chat_model, messages=messages)
            return response['message']['content']
        except Exception as e:
            print(f"Error getting chat response: {e}", file=sys.stderr)
            return "Error generating feedback."