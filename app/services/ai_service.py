import requests
import json
import re
from app.schemas.information import ExtractionResponse

class OllamaService:

    @staticmethod
    def extract_information(text: str):

        url = "http://localhost:11434/api/generate"

        prompt_template = """
        You are a professional information extraction and news structuring AI.

        Your job is to convert raw documents into HIGH-QUALITY structured information for a news system.

        You MUST follow ALL rules strictly.

        ----------------------------------------------------
        OUTPUT FORMAT (ONLY JSON):
        ----------------------------------------------------:

        {
        "information": [
            {
            "type": "",
            "title": "",
            "summary": "",
            "fields": {}
            }
        ]
        }

        ----------------------------------------------------
        CRITICAL RULES:
        ----------------------------------------------------

        1. SUMMARY RULES:
        - Must NOT be empty
        - Must be 1–2 clear sentences
        - Must be written in formal news style
        - Must not repeat the title only

        2. TYPE RULES:
        Use ONLY these types:
        - Meeting
        - Finance
        - Event
        - Health
        - Announcement
        - Project
        - Emergency
        - Education
        - General

        If unsure → use "General"

        3. FIELD RULES (VERY IMPORTANT):
        - Extract ONLY factual information
        - Normalize values properly

        Examples:
        - amount → always include currency (RM, USD, etc.)
        - date → use readable format (e.g. 2026-06-15 if possible)
        - location → clean location name only

        Finance fields:
        - amount
        - purpose
        - source

        Meeting fields:
        - date
        - location
        - decisions (if any)
        - agenda (if any)

        Event fields:
        - date
        - location
        - organizer (if mentioned)

        Health fields:
        - date
        - organization
        - purpose

        Announcement fields:
        - date
        - issuer
        - topic

        4. IMPORTANT RULES:
        - NEVER leave summary empty
        - NEVER leave fields empty if data exists
        - NEVER add explanations outside JSON
        - MUST extract multiple information items if present

        ----------------------------------------------------
        DOCUMENT:
        ----------------------------------------------------

        {text}
        """

        prompt = prompt_template.replace("{text}", text)

        response = requests.post(
            url,
            json={
                "model": "llama3.1",
                "prompt": prompt,
                "stream": False
            }
        )

        raw = response.json()["response"]

        raw_json = OllamaService._safe_json(raw)

        try:
            validated = ExtractionResponse(**raw_json)
            return validated.model_dump()
        except Exception as e:

            # STEP 2: auto fix attempt
            fixed = OllamaService.fix_json_with_ai(raw)

            try:
                validated = ExtractionResponse(**fixed)
                return validated.model_dump()

            except Exception as e2:
                return {
                    "error": "Schema validation failed after retry",
                    "details": str(e2),
                    "raw_output": raw_json,
                    "fixed_output": fixed
                }

    @staticmethod
    def _safe_json(text: str):

        # 1. Try direct JSON parse
        try:
            return json.loads(text)
        except:
            pass

        # 2. Extract JSON inside ``` blocks
        try:
            match = re.search(r"```(?:json)?(.*?)```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1).strip())
        except:
            pass

        # 3. Extract raw JSON object
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except:
            pass

        # 4. Final fallback
        return {
            "error": "Invalid JSON from model",
            "raw_output": text
        }
    
    @staticmethod
    def fix_json_with_ai(raw_output: str):

        url = "http://localhost:11434/api/generate"

        prompt = f"""
    You are a strict JSON repair engine.

    Convert the following into VALID JSON ONLY.

    RULES:
    - Output ONLY JSON
    - No explanation
    - No markdown
    - No backticks

    Broken data:
    {raw_output}
    """

        response = requests.post(
            url,
            json={
                "model": "llama3.1",
                "prompt": prompt,
                "stream": False
            }
        )

        raw_text = response.json()["response"]

        # 🔥 IMPORTANT: parse again using your safe parser
        return OllamaService._safe_json(raw_text)