
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

from app.retriever import KnowledgeRetriever


MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

# Tune this using tests on relevant and irrelevant questions.
MIN_RELEVANCE_SCORE = 0.35
TOP_K = 3
MAX_NEW_TOKENS = 220

GEMINI_MODEL = "gemini-3.5-flash-lite"


class ITHelpdeskRAG:
   def __init__(self):
    self.llm_provider = os.getenv("LLM_PROVIDER", "local").lower()

    if self.llm_provider == "gemini":
        print("Initializing Gemini API...")

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing.")

        self.gemini_client = genai.Client(api_key=api_key)
        self.tokenizer = None
        self.model = None

    elif self.llm_provider == "local":
        print("Loading Qwen model...")
        # Local model imports
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            dtype="auto",
            low_cpu_mem_usage=True
        )

        self.model.eval()
        self.gemini_client = None

    else:

        
        raise ValueError(
            f"Unsupported LLM_PROVIDER: {self.llm_provider}"
        )

    print("Loading knowledge retriever...")
    self.retriever = KnowledgeRetriever()

    print("IT Helpdesk RAG is ready.")


   def is_answer_supported(self, answer_text: str, context: str) -> bool:
    """
    Basic check for whether the answer contains unsupported details.
    """
    answer_lower = answer_text.lower()
    context_lower = context.lower()

    unsupported_phrases = [
    "email address",
    "phone number",
    "clicking on the link",
    "another browser",
    "different browser",
    "clear your cache",
    "required fields correctly",
    "verify your email",
    "compatible with their current system",
    "download the installer",
    "official source",
    "run the installer as an administrator",
    "setup prompts",
    "restart the computer",
    "ip address",
    "hostname",
    "both your computer",
    "date/time"
 ]

    return not any(
        phrase in answer_lower and phrase not in context_lower
        for phrase in unsupported_phrases
    )

   def answer(self, question: str) -> dict:
        if not question or not question.strip():
         return {
            "answer": "Please enter an IT support question.",
            
            "sources": [],
            "needs_escalation": False,
            "relevance_score": None
    }

        results = self.retriever.search(question, top_k=TOP_K)

        # Check whether the best retrieved passage is relevant enough.
        if not results or results[0]["score"] < MIN_RELEVANCE_SCORE:
           return {
             "answer": (
             "I could not find sufficiently relevant information "
             "in the available IT knowledge base. Please contact "
             "the IT support team or create a support ticket."
        ),

            "sources": [],
            "needs_escalation": True,
            "relevance_score": (
                round(results[0]["score"], 4)
                if results else None
        )
    }

        # Include only passages that meet the configured threshold.
        relevant_results = [
            result for result in results
            if result["score"] >= MIN_RELEVANCE_SCORE
        ]

        context = "\n\n".join(
            f"Source: {item['source']}\n"
            f"Knowledge: {item['text']}"
            for item in relevant_results
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an enterprise IT helpdesk assistant. "
                    "Answer strictly using the supplied knowledge context. "
                    "Never invent, assume, or add troubleshooting steps, "
                    "verification methods, policies, or technical details. "
                    "Only provide steps explicitly mentioned in the context. "
                    "Do not use general IT knowledge to fill missing information. "
                    "If the context does not explain how to resolve the user's issue, "
                    "do not generate troubleshooting instructions. "
                    "Clearly state that the available knowledge base does not provide "
                    "enough information and recommend contacting authorized IT support. "
                    "Give numbered steps only when those steps are explicitly supported. "
                    "Never request passwords or verification codes."
                                    )
            },
            {
                "role": "user",
                "content": (
                    f"Knowledge context:\n{context}\n\n"
                    f"Employee question: {question}\n\n"
                    "Provide a concise, helpful answer based on the context."
                )
            }
        ]

        

        if self.llm_provider == "gemini":

            prompt = (
                f"{messages[0]['content']}\n\n"
                f"{messages[1]['content']}"
            )

            response = self.gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={
                    "temperature": 0.2,
                    "max_output_tokens": MAX_NEW_TOKENS
                }
            )

            answer_text = response.text.strip() if response.text else (
                "I could not generate a response. Please contact IT support."
            )

        else:

            inputs = self.tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True
            )

            with torch.inference_mode():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=MAX_NEW_TOKENS,
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            new_tokens = outputs[0, inputs["input_ids"].shape[1]:]

            answer_text = self.tokenizer.decode(
                new_tokens,
                skip_special_tokens=True
            ).strip()


        
        if not self.is_answer_supported(answer_text, context):
            answer_text = (
            "The available knowledge base does not provide enough "
            "information to resolve this issue. Please contact "
            "authorized IT support or create a support ticket."
            )
            needs_escalation = True
        else:
            needs_escalation = False


        sources = [
            {
                "source": item["source"],
                "score": round(item["score"], 4)
            }
            for item in relevant_results
        ]

        return {
        "answer": answer_text,
        "sources": sources,
        "needs_escalation": needs_escalation,
        "relevance_score": round(results[0]["score"], 4)
    }


if __name__ == "__main__":
    assistant = ITHelpdeskRAG()

    print("\n=== ServiceNow Virtual Agent with RAG ===")
    print("Type 'exit' to quit.")

    while True:
        question = input("\nAsk an IT question: ").strip()

        if question.lower() in {"exit", "quit"}:
            break

        try:
            result = assistant.answer(question)

            print("\nAssistant:")
            print(result["answer"])

            print("\nSources:")
            if result["sources"]:
                for source in result["sources"]:
                    print(
                        f"- {source['source']} "
                        f"(score: {source['score']})"
                    )
            else:
                print("- No sufficiently relevant source found.")

        except Exception as error:
            print(f"\nAn error occurred: {error}")
