import sys
import types
try:
    import langchain_community.chat_models
    sys.modules["langchain_community.chat_models.vertexai"] = types.ModuleType("vertexai")
    sys.modules["langchain_community.chat_models.vertexai"].ChatVertexAI = object
except:
    pass

import json
import os
from pathlib import Path
import pandas as pd

# You will need to install these packages for hosted API evaluation:
# pip install ragas langchain-openai langchain-community datasets pandas sentence-transformers

try:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy
    
    # Use the configured hosted evaluator endpoint.
    from langchain_openai import ChatOpenAI
    # Use HuggingFace for local embeddings
    from langchain_community.embeddings import HuggingFaceEmbeddings
except ImportError:
    print("Please install requirements first:")
    print("pip install ragas langchain-openai langchain-community datasets pandas sentence-transformers")
    exit(1)

def run_evaluation(evaluation_results_path: str):
    if not os.path.exists(evaluation_results_path):
        print(f"File not found: {evaluation_results_path}. Run evaluate_editorial.py first.")
        return

    data = json.loads(Path(evaluation_results_path).read_text())
    
    questions = []
    contexts = []
    answers = []
    
    root = Path(__file__).resolve().parents[1]
    original_cases = {c['id']: c for c in json.loads((root / 'evaluation/editorial_cases.json').read_text())}

    for result_case in data.get('cases', []):
        case_id = result_case['id']
        original_case = original_cases.get(case_id)
        
        article = result_case.get('result', {}).get('article')
        if not article or not original_case:
            continue
            
        questions.append(original_case['instructions'])
        contexts.append([original_case['information']])
        body_text = article.get("body", [])
        if isinstance(body_text, list): body_text = "\n".join(body_text)
        answers.append(body_text or article.get("summary", ""))

    if not answers:
        print("No drafted articles found in the evaluation output to score.")
        return

    dataset = Dataset.from_dict({
        "question": questions,
        "contexts": contexts,
        "answer": answers,
    })

    sys.path.insert(0, str(root))
    from app.core.config import Settings
    settings = Settings()
    if not settings.evaluator_api_key or not settings.evaluator_model:
        raise ValueError("Set EVALUATOR_API_KEY and EVALUATOR_MODEL before evaluation")
    print(f"Evaluating {len(dataset)} articles using the hosted evaluator...")
    eval_llm = ChatOpenAI(
        model=settings.evaluator_model,
        api_key=settings.evaluator_api_key,
        base_url=settings.evaluator_base_url,
        timeout=settings.evaluator_timeout_seconds,
        max_retries=1,
    )

    # 2. Run fast local embeddings directly in Python (no server needed)
    print("Loading local embedding model...")
    eval_embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Run Ragas Evaluation
    print("Running evaluation metrics (this may take a few minutes)...")
    result = evaluate(
        dataset,
        metrics=[faithfulness],
        llm=eval_llm,
        embeddings=eval_embeddings,
    )

    df = result.to_pandas()
    df.to_csv("fyp_evaluation_metrics.csv", index=False)
    
    print("\n--- Ragas Evaluation Complete ---")
    print(result)
    print("Detailed metrics saved to fyp_evaluation_metrics.csv")

if __name__ == "__main__":
    run_evaluation("/tmp/agent-evaluation.json")
