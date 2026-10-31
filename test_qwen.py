
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

print("Loading Qwen tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

print("Loading Qwen model...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype="auto",
    low_cpu_mem_usage=True
)

model.eval()

messages = [
    {
        "role": "system",
        "content": (
            "You are a helpful enterprise IT helpdesk assistant. "
            "Give clear, safe, step-by-step troubleshooting instructions."
        )
    },
    {
        "role": "user",
        "content": "My VPN is not connecting. How can I troubleshoot it?"
    }
]

inputs = tokenizer.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_tensors="pt"
)

print("\nGenerating answer...\n")

with torch.no_grad():
    outputs = model.generate(
        inputs,
        max_new_tokens=180,
        do_sample=False
    )

answer = tokenizer.decode(
    outputs[0][inputs.shape[-1]:],
    skip_special_tokens=True
)

print("Qwen response:")
print(answer)
