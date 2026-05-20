import json
import re
import requests
from typing import Dict, Any, List
from models.anxiety_model import AnxietyAnalyzer
from models.personality_model import PersonalityAnalyzer
from datetime import datetime


class AnalysisService:
    """Сервис для выполнения всех типов анализа"""

    def __init__(self, anxiety_model_path, personality_base_model, personality_lora_path):
        self.anxiety_model_path = anxiety_model_path
        self.personality_base_model = personality_base_model
        self.personality_lora_path = personality_lora_path

        self._anxiety_analyzer = None
        self._personality_analyzer = None

        self.ollama_url = "http://localhost:11434"

        self.cloud_models = [
            "gpt-oss:120b-cloud",
            "qwen3-next:80b-cloud"
        ]

    @property
    def anxiety_analyzer(self):
        if self._anxiety_analyzer is None:
            print("ЗАГРУЗКА ЛОКАЛЬНОЙ МОДЕЛИ ТРЕВОЖНОСТИ...")
            self._anxiety_analyzer = AnxietyAnalyzer(self.anxiety_model_path)
            print("ЛОКАЛЬНАЯ МОДЕЛЬ ТРЕВОЖНОСТИ ЗАГРУЖЕНА!")
        return self._anxiety_analyzer

    @property
    def personality_analyzer(self):
        if self._personality_analyzer is None:
            print("Загрузка модели личности...")
            self._personality_analyzer = PersonalityAnalyzer(
                base_model_name=self.personality_base_model,
                lora_weights_path=self.personality_lora_path
            )
            print("Модель личности загружена!")
        return self._personality_analyzer

    def check_available_models(self) -> List[str]:
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                if models:
                    return [m['name'] for m in models]
        except:
            pass
        return self.cloud_models

    def _call_cloud_model(self, prompt: str, model_name: str) -> str:
        print(f"Вызов облачной модели: {model_name}")
        print(f"Промпт: {prompt[:200]}...")

        data = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }

        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json=data,
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '')
            print(f"Ответ модели: {response_text[:200]}...")
            return response_text
        else:
            raise Exception(f"Ошибка API: {response.status_code}")

    def analyze_anxiety(self, text: str, model_type: str = 'local',
                        user_info: str = '', cloud_model: str = '') -> Dict[str, Any]:
        """
        Анализ тревожности
        """
        print(f"\n{'=' * 50}")
        print(f"АНАЛИЗ ТРЕВОЖНОСТИ: model_type={model_type}")
        print(f"{'=' * 50}")

        if model_type == 'local':
            print(">>> ИСПОЛЬЗУЕМ ЛОКАЛЬНУЮ МОДЕЛЬ <<<")
            result = self.anxiety_analyzer.analyze(text)
            print(f"Результат локальной модели: {result}")

            return {
                'type': 'anxiety',
                'model_type': 'local',
                'model_name': 'local_anxiety_model',
                'result': result
            }
        else:
            print(">>> ИСПОЛЬЗУЕМ ОБЛАЧНУЮ МОДЕЛЬ <<<")

            system_prompt = (
                "Ты клинический психолог. Определи, есть ли у пользователя признаки тревожности. "
                "Ответь строго в формате:\n"
                "Диагноз: [ТРЕВОЖНОСТЬ/НЕТ ТРЕВОЖНОСТИ]\n"
                "Обоснование: [1 предложение]"
            )

            prompt = f"{system_prompt}\n\nТекст для анализа:\n{text}"

            models_to_try = [cloud_model] if cloud_model else self.cloud_models

            for model_name in models_to_try:
                try:
                    response = self._call_cloud_model(prompt, model_name)
                    parsed = self._parse_anxiety_response(response)

                    return {
                        'type': 'anxiety',
                        'model_type': 'cloud',
                        'model_name': model_name,
                        'result': parsed,
                        'raw_response': response
                    }
                except Exception as e:
                    print(f"Ошибка с моделью {model_name}: {e}")
                    continue

            raise Exception("Все облачные модели недоступны")

    def analyze_big5(self, text: str, model_type: str = 'local',
                     user_info: str = '', cloud_model: str = '') -> Dict[str, Any]:
        """Анализ по Big5"""
        if model_type == 'local':
            result = self.personality_analyzer.analyze(text, user_info)
            return {
                'type': 'big5',
                'model_type': 'local',
                'model_name': 'local_big5_model',
                'result': result
            }
        else:
            prompt = self._create_big5_prompt(text, user_info)
            models_to_try = [cloud_model] if cloud_model else self.cloud_models

            for model_name in models_to_try:
                try:
                    response = self._call_cloud_model(prompt, model_name)
                    parsed = self._parse_big5_response(response)
                    return {
                        'type': 'big5',
                        'model_type': 'cloud',
                        'model_name': model_name,
                        'result': parsed,
                        'raw_response': response
                    }
                except Exception as e:
                    print(f"Ошибка с моделью {model_name}: {e}")
                    continue

            raise Exception("Все облачные модели недоступны")

    def analyze_full(self, text: str, model_type: str = 'cloud',
                     user_info: str = '', cloud_model: str = '') -> Dict[str, Any]:
        """Полный анализ"""
        prompt = self._create_full_analysis_prompt(text, user_info)
        models_to_try = [cloud_model] if cloud_model else self.cloud_models

        for model_name in models_to_try:
            try:
                response = self._call_cloud_model(prompt, model_name)
                parsed = self._parse_full_analysis_response(response)
                return {
                    'type': 'full',
                    'model_type': 'cloud',
                    'model_name': model_name,
                    'result': parsed,
                    'raw_response': response
                }
            except Exception as e:
                print(f"Ошибка с моделью {model_name}: {e}")
                continue

        raise Exception("Все облачные модели недоступны")

    def _parse_anxiety_response(self, response: str) -> Dict[str, Any]:
        """Парсинг ответа модели тревожности"""
        print(f"\nПАРСИНГ ОТВЕТА:")
        print(f"Ответ: {response[:300]}")

        diagnosis = "НЕТ ТРЕВОЖНОСТИ"
        rationale = ""

        if "Диагноз:" in response:
            diag_part = response.split("Диагноз:")[-1].strip()
            print(f"Часть с диагнозом: {diag_part[:100]}")

            if "ТРЕВОЖНОСТЬ" in diag_part.upper():
                if "НЕТ ТРЕВОЖНОСТИ" not in diag_part.upper():
                    diagnosis = "ТРЕВОЖНОСТЬ"
                    print(">>> НАЙДЕНА ТРЕВОЖНОСТЬ <<<")

        if "Обоснование:" in response:
            rationale = response.split("Обоснование:")[-1].strip()
            if '\n' in rationale:
                rationale = rationale.split('\n')[0].strip()
            if '.' in rationale:
                rationale = rationale.split('.')[0].strip() + '.'
            print(f"Обоснование: {rationale[:100]}")

        if not rationale and '{' in response:
            try:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    if data.get('has_anxiety'):
                        diagnosis = "ТРЕВОЖНОСТЬ"
                    if data.get('analysis'):
                        rationale = data['analysis']
            except:
                pass

        result = {
            "diagnosis": diagnosis,
            "rationale": rationale if rationale else "Не удалось извлечь обоснование",
            "analysis": rationale if rationale else "Не удалось извлечь обоснование",
            "has_anxiety": diagnosis == "ТРЕВОЖНОСТЬ",
            "raw_output": response
        }

        print(f"ИТОГ: {result['diagnosis']} | {result['rationale'][:100]}")
        return result

    def _parse_big5_response(self, response: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return {"error": "Не удалось распарсить ответ", "raw_response": response}

    def _parse_full_analysis_response(self, response: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return {"error": "Не удалось распарсить ответ", "raw_response": response}

    def _create_big5_prompt(self, text: str, user_info: str) -> str:
        return f"""Выполни анализ личности по модели Big Five.
Оцени каждую черту от 0 до 100.
Ответ предоставь строго в JSON-формате.

Информация: {user_info if user_info else 'Не указана'}

Текст: {text}

Формат ответа:
{{
    "traits": {{
        "открытость_опыту": {{"score": 0-100, "level": "низкий/средний/высокий", "description": "описание"}},
        "добросовестность": {{"score": 0-100, "level": "низкий/средний/высокий", "description": "описание"}},
        "экстраверсия": {{"score": 0-100, "level": "низкий/средний/высокий", "description": "описание"}},
        "доброжелательность": {{"score": 0-100, "level": "низкий/средний/высокий", "description": "описание"}},
        "нейротизм": {{"score": 0-100, "level": "низкий/средний/высокий", "description": "описание"}}
    }}
}}"""

    def _create_full_analysis_prompt(self, text: str, user_info: str) -> str:
        """Создание промпта для полного анализа"""
        return f"""# Задача
Выполните комплексный психологический анализ личности пользователя на основе предоставленного текста.

# Контекст
Информация о пользователе: {user_info if user_info else 'Не указана'}

# Текст для анализа
{text}

# Требования к анализу
1. Оцените уровень тревожности (0-10)
2. Проведите анализ по Big Five (оценки 0-100)
3. На основе полученных результатов сделайте общий анализ

# Формат ответа
Предоставьте ответ в JSON-формате:
{{
    "anxiety": {{
        "level": число,
        "type": "тип тревожности",
        "description": "описание"
    }},
    "big5": {{
        "открытость_опыту": {{"score": число, "level": "уровень"}},
        "добросовестность": {{"score": число, "level": "уровень"}},
        "экстраверсия": {{"score": число, "level": "уровень"}},
        "доброжелательность": {{"score": число, "level": "уровень"}},
        "нейротизм": {{"score": число, "level": "уровень"}}
    }},
    "summary": "общее резюме"
}}"""