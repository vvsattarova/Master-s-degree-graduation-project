# models/personality_model.py
import torch
import re
import json
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


class PersonalityAnalyzer:
    """
    Класс для анализа личности по тексту с использованием обученной модели
    """

    def __init__(
            self,
            base_model_name="Vikhrmodels/Vikhr-Qwen-2.5-0.5B-Instruct",
            lora_weights_path="personality_model_vikhr/lora_weights",
            device="auto"
    ):
        """
        Инициализация анализатора личности
        """
        print("Загрузка модели Big5...")

        # Определяем устройство
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        print(f"Используемое устройство: {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            base_model_name,
            trust_remote_code=True
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        print("Загрузка базовой модели...")
        self.model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map=self.device,
            trust_remote_code=True
        )

        print("Загрузка LoRA весов...")
        self.model = PeftModel.from_pretrained(self.model, lora_weights_path)
        self.model.eval()

        self.generation_config = {
            "max_new_tokens": 100,
            "do_sample": False,
            "pad_token_id": self.tokenizer.eos_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }

        self.trait_names = [
            "открытость_опыту",
            "добросовестность",
            "экстраверсия",
            "доброжелательность",
            "нейротизм"
        ]

        self.trait_descriptions = {
            "открытость_опыту": "любознательность, креативность, воображение",
            "добросовестность": "организованность, дисциплина, надёжность",
            "экстраверсия": "общительность, энергичность, социальная активность",
            "доброжелательность": "эмпатия, сотрудничество, доверие к людям",
            "нейротизм": "эмоциональная нестабильность, тревожность"
        }

        self.level_names = {0: "низкий", 1: "средний", 2: "высокий"}

        print("Модель Big5 готова к анализу!")

    def create_prompt(self, text, user_info=None):
        """Создает промпт для анализа личности"""
        prompt = f"""# Задача
Выполните анализ личности пользователя социальной сети на основе его публикаций. Оцените каждую из пяти черт личности по шкале: 0 - низкий уровень, 1 - средний уровень, 2 - высокий уровень. Ответ предоставьте строго в JSON-формате без дополнительного текста.

# Описание черт личности
- Открытость опыту: любознательность, креативность, воображение, интерес к новым идеям и эстетическим переживаниям
- Добросовестность: организованность, дисциплина, надёжность, целеустремлённость, внимание к деталям
- Экстраверсия: общительность, энергичность, напористость, склонность к социальным взаимодействиям
- Доброжелательность: эмпатия, готовность помогать, доверие к людям, склонность к сотрудничеству
- Нейротизм: эмоциональная нестабильность, тревожность, раздражительность, подверженность стрессу

# Информация о пользователе
{user_info if user_info else 'Не указана'}

# Публикации пользователя
{text}

# Формат ответа
"""
        return prompt

    def extract_json(self, text):
        """Извлекает JSON из текста ответа модели"""
        # Стратегия 1: Ищем точное совпадение с ключами
        json_pattern = r'\{[^{}]*"открытость_опыту"[^{}]*\}'
        match = re.search(json_pattern, text)
        if match:
            try:
                result = json.loads(match.group())
                if all(key in result for key in self.trait_names):
                    return result
            except json.JSONDecodeError:
                pass

        # Стратегия 2: Ищем любой JSON с нужными ключами
        json_pattern = r'\{[^{}]*\}'
        matches = re.findall(json_pattern, text)
        for match_str in matches:
            try:
                result = json.loads(match_str)
                if all(key in result for key in self.trait_names):
                    return result
            except json.JSONDecodeError:
                continue

        # Стратегия 3: Пытаемся найти значения по ключам в тексте
        result = {}
        for trait in self.trait_names:
            pattern = f'"{trait}"\\s*:\\s*(\\d)'
            match = re.search(pattern, text)
            if match:
                result[trait] = int(match.group(1))

        if len(result) == 5:
            return result

        return None

    def analyze(self, text, user_info=None):
        """Анализирует личность по тексту"""
        print(f"\nАнализ текста (длина: {len(text)} символов)...")

        # Создаем промпт
        prompt = self.create_prompt(text, user_info)

        # Токенизируем
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        )
        input_ids = inputs.input_ids.to(self.model.device)
        attention_mask = inputs.attention_mask.to(self.model.device)

        # Генерируем ответ
        print("Генерация ответа...")
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids,
                attention_mask=attention_mask,
                max_new_tokens=100,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        # Декодируем
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"Сгенерированный текст: {generated_text[:200]}...")

        # Извлекаем JSON
        predictions = self.extract_json(generated_text)
        print(f"Извлеченные predictions: {predictions}")

        # Формируем результат
        result = {
            "raw_output": generated_text,
            "predictions": predictions,
            "analysis": {}
        }

        if predictions:
            for trait in self.trait_names:
                score = int(predictions[trait])
                result["analysis"][trait] = {
                    "score": score,
                    "level": self.level_names.get(score, "неизвестно"),
                    "description": self.trait_descriptions[trait]
                }
        else:
            # Если не удалось извлечь predictions, создаем заглушку
            print("ВНИМАНИЕ: Не удалось извлечь predictions!")
            result["analysis"] = {
                trait: {
                    "score": 1,
                    "level": "средний",
                    "description": self.trait_descriptions[trait]
                }
                for trait in self.trait_names
            }

        return result

    def print_analysis(self, result):
        """Красиво выводит результаты анализа"""
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТЫ АНАЛИЗА ЛИЧНОСТИ")
        print("=" * 60)

        if result["predictions"] is None:
            print("❌ Не удалось извлечь оценки из ответа модели")
            print(f"\nСырой вывод модели:\n{result['raw_output'][:500]}...")
            return

        print("\n📊 Профиль личности:")
        print("-" * 40)

        for trait, info in result["analysis"].items():
            trait_name = trait.replace("_", " ").title()
            level = info["level"]
            score = info["score"]

            # Визуализация шкалы
            bar = "█" * (score + 1) + "░" * (2 - score)

            print(f"{trait_name:20} [{bar}] {level.title()} ({score}/2)")

        print("=" * 60)