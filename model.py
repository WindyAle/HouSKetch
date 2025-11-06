from ollama import Client
import sys
import os
from dotenv import load_dotenv

load_dotenv()
POD_ID = os.getenv("POD_ID")

# RunPod에서 제공하는 Ollama 엔드포인트
RUNPOD_HOST_URL = f"https://{POD_ID}-11434.proxy.runpod.net"

class ModelManager:
    """
    Ollama 서버와의 모든 통신을 관리하는 클래스입니다.
    연결 확인, 모델(EEVE, Chat) 준비, 임베딩 생성을 담당합니다.
    """
    def __init__(self, embedding_model='EEVE-Korean-10.8B', chat_model='llama3'):
        print("=== 모델 초기화 중... ===")
        self.embedding_model = embedding_model
        self.chat_model = chat_model
        self.is_ready = False

        # --- (수정) RunPod에 연결하는 Client 생성 ---
        try:
            # 지정된 RunPod URL로 Client 생성
            self.client = Client(host=RUNPOD_HOST_URL)
            print(f"RunPod에 연결합니다...")
        
            self._initialize_ollama()

        except Exception as e:
            print(f"🚨 Client 생성 실패: {e}", file=sys.stderr)
            print("RunPod URL이 정확한지, Ollama가 해당 포트에서 실행 중인지 확인하세요.")
            self.is_ready = False

    def _initialize_ollama(self):
        """
        Ollama 서버에 연결하고 필요한 모델이 있는지 확인합니다.
        없으면 모델을 pull 합니다.
        """
        try:
            self.client.list()
            print("🦙 Ollama 연결 완료\n")
            
            # 필요한 모델 목록
            required_models_name = [self.embedding_model, self.chat_model]

            # 실제로 받아온 모델 목록 (위와 비교)
            model_list = self.client.list()['models']
            available_models = [model['model'] for model in model_list]

            for model_name in required_models_name:
                # 모델 이름에 특수문자를 포함할 수 있으므로 startswith로 검사
                if not any(m.startswith(model_name) for m in available_models):
                    print(f"🚨 모델 '{model_name}' 없음. Pull하는 중...")
                    self.client.pull(model_name)
                    print(f"✅ 모델 '{model_name}' Pull 완료")
                else:
                    print(f"✅ 모델 '{model_name}' 준비 완료")
            print()
            
            self.is_ready = True

        except Exception as e:
            print(f"Error: {e}\n", file=sys.stderr)
            self.is_ready = False

    def get_embedding(self, text: str) -> list[float]:
        """
        주어진 텍스트를 EEVE를 사용해 의미 벡터로 변환합니다.
        """
        if not self.is_ready or not text:
            return []
            
        try:
            response = self.client.embeddings(model=self.embedding_model, prompt=text)
            return response['embedding']
        except Exception as e:
            print(f"Error from 'get_embedding()': {e}", file=sys.stderr)
            return []
            
    # 모델 프롬프트 응답
    def get_chat_response(self, system_prompt: str, user_prompt: str) -> str:
        """
        채팅 모델을 사용해 자연어 응답을 생성합니다.
        """
        if not self.is_ready:
            return "🚨 모델이 준비되지 않음"
            
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
                {'role': 'assistant', 'content': "아늑하고 소파와 테이블이 있는 작은 거실이 좋아요."}
            ]
            options = {
                "temperature": 0.7,
                "num_ctx": 2048,
                "top_p": 1,
                "num_predict": 1000
            }

            response = self.client.chat(
                model=self.chat_model, 
                messages=messages,
                options=options
            )

            return response['message']['content']
        except Exception as e:
            print(f"Error 'get_chat_response()': {e}", file=sys.stderr)
            return "🚨 피드백 생성 중 오류"