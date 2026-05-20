# models/anxiety_model.py
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnxietyAnalyzer:
    """
    Класс для анализа тревожности в текстах.
    Модель определяет: есть тревожность или нет + обоснование.
    """

    def __init__(
            self,
            model_path: str = "anxiety_model",
            device: Optional[str] = None,
            system_prompt: Optional[str] = None,
            load_in_4bit: bool = True
    ):
        self.model_path = model_path

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.system_prompt = system_prompt or (
            "Ты клинический психолог. Определи, есть ли у пользователя признаки тревожности. "
            "Ответь строго в формате:\n"
            "Диагноз: [ТРЕВОЖНОСТЬ/НЕТ ТРЕВОЖНОСТИ]\n"
            "Обоснование: [1 предложение]"
        )

        self._load_model(load_in_4bit)
        logger.info(f"AnxietyAnalyzer инициализирован на устройстве: {self.device}")

    def _load_model(self, load_in_4bit: bool) -> None:
        try:
            logger.info(f"Загрузка модели из: {self.model_path}")

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.padding_side = "right"

            if load_in_4bit and self.device == "cuda":
                try:
                    from transformers import BitsAndBytesConfig
                    bnb_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_compute_dtype=torch.bfloat16,
                        bnb_4bit_use_double_quant=True,
                    )
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_path,
                        quantization_config=bnb_config,
                        device_map="auto",
                        trust_remote_code=True,
                    )
                except ImportError:
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_path,
                        device_map="auto",
                        trust_remote_code=True,
                        torch_dtype=torch.float16,
                    )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    device_map="auto" if self.device == "cuda" else "cpu",
                    trust_remote_code=True,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                )

            self.model.eval()
            logger.info("Модель успешно загружена")

        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            raise

    def _format_prompt(self, text: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": text}
        ]

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        return prompt

    def _generate_response(self, prompt: str) -> str:
        """Генерация ответа модели"""
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=inputs.input_ids,
                attention_mask=inputs.attention_mask,
                max_new_tokens=100,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        if "assistant" in response:
            response = response.split("assistant")[-1].strip()

        return response

    def _parse_response(self, response: str) -> Dict:
        diagnosis = "НЕТ ТРЕВОЖНОСТИ"
        rationale = ""

        if "Диагноз:" in response:
            diag_part = response.split("Диагноз:")[-1].strip()
            if "ТРЕВОЖНОСТЬ" in diag_part.upper():
                if "НЕТ ТРЕВОЖНОСТИ" not in diag_part.upper():
                    diagnosis = "ТРЕВОЖНОСТЬ"

        if "Обоснование:" in response:
            rationale = response.split("Обоснование:")[-1].strip()
            # Убираем все после точки
            if '.' in rationale:
                rationale = rationale.split('.')[0].strip() + '.'
            rationale = rationale.replace('Диагноз:', '').strip()

        logger.info(f"Парсинг ответа: диагноз={diagnosis}, обоснование={rationale[:100]}")

        return {
            "diagnosis": diagnosis,
            "rationale": rationale,
            "raw_response": response
        }

    def analyze(self, text: str) -> Dict:
        """
        Анализ текста на наличие тревожности.
        Возвращает ТОЛЬКО диагноз и обоснование.
        """
        if not text or not isinstance(text, str) or len(text.strip()) < 10:
            return {
                "diagnosis": "НЕТ ТРЕВОЖНОСТИ",
                "rationale": "Текст слишком короткий для анализа",
                "analysis": "Текст слишком короткий для анализа",
                "raw_output": "",
                "has_anxiety": False
            }

        try:
            prompt = self._format_prompt(text)

            # Получаем ответ модели
            response = self._generate_response(prompt)

            # Парсим ответ
            parsed = self._parse_response(response)

            return {
                "diagnosis": parsed["diagnosis"],
                "rationale": parsed["rationale"],
                "analysis": parsed["rationale"],  # Для совместимости
                "raw_output": parsed["raw_response"],
                "has_anxiety": parsed["diagnosis"] == "ТРЕВОЖНОСТЬ"
            }

        except Exception as e:
            logger.error(f"Ошибка при анализе текста: {e}")
            return {
                "diagnosis": "НЕТ ТРЕВОЖНОСТИ",
                "rationale": f"Ошибка анализа: {str(e)}",
                "analysis": f"Ошибка анализа: {str(e)}",
                "raw_output": "",
                "has_anxiety": False,
                "error": str(e)
            }