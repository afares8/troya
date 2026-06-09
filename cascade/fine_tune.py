"""Fine-tuning infrastructure for local model customization with LoRA."""

import json
import random
from pathlib import Path
from typing import Any

from .ui import print_error, print_info, print_success, print_warning


class FineTuner:
    """Prepare datasets and scripts for local fine-tuning with LoRA/QLoRA."""

    def __init__(self, model_name: str = "unsloth/llama-3-8b", output_dir: Path | None = None) -> None:
        self.model_name = model_name
        self.output_dir = output_dir or Path.home() / ".config" / "cascade-cli" / "finetune"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def prepare_from_project(self, project_root: Path, max_examples: int = 500) -> Path:
        """Generate instruction-following dataset from project code."""
        dataset: list[dict[str, str]] = []

        # Collect code files
        code_files = []
        for ext in (".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp"):
            code_files.extend(project_root.rglob(f"*{ext}"))

        code_files = [f for f in code_files if f.stat().st_size < 20_000][:max_examples]

        print_info(f"Found {len(code_files)} code files for dataset generation")

        for filepath in code_files:
            try:
                content = filepath.read_text(encoding="utf-8").strip()
            except (UnicodeDecodeError, OSError):
                continue
            if len(content) < 100 or len(content) > 4000:
                continue

            # Generate instruction-output pairs
            filename = filepath.name
            examples = self._generate_examples(filename, content)
            dataset.extend(examples)

        # Save dataset
        dataset_path = self.output_dir / "dataset.jsonl"
        with open(dataset_path, "w", encoding="utf-8") as f:
            for item in dataset:
                f.write(json.dumps(item) + "\n")

        # Save training script
        self._save_training_script()
        self._save_inference_script()

        print_success(f"Generated {len(dataset)} training examples")
        return dataset_path

    def _generate_examples(self, filename: str, code: str) -> list[dict[str, str]]:
        """Create instruction-following examples from code snippets."""
        examples = []

        # Example 1: Explain this code
        examples.append({
            "instruction": f"Explain what the code in {filename} does.",
            "input": code[:2000],
            "output": f"This is a code file named {filename} containing programming logic."
        })

        # Example 2: Generate similar code
        examples.append({
            "instruction": f"Write a code snippet similar to {filename}.",
            "input": "",
            "output": code[:2000]
        })

        # Example 3: Fix bugs
        if "def " in code:
            examples.append({
                "instruction": f"Review this code from {filename} and suggest improvements.",
                "input": code[:2000],
                "output": "The code appears well-structured. Consider adding docstrings and type hints for better maintainability."
            })

        # Example 4: Generate docstring
        lines = code.split("\n")
        for line in lines:
            if line.strip().startswith("def ") and "(" in line:
                func_name = line.strip().split("def ")[1].split("(")[0]
                examples.append({
                    "instruction": f"Write a docstring for function '{func_name}' in {filename}.",
                    "input": line.strip(),
                    "output": f'"""{func_name} function.\n\nArgs:\n    Various parameters.\n\nReturns:\n    Result of operation.\n"""'
                })
                break  # Only one per file

        return examples

    def _save_training_script(self) -> None:
        script = '''"""Training script for Cascade fine-tuning.

Install dependencies:
    pip install unsloth torch transformers trl peft accelerate bitsandbytes

Run training:
    python train.py
"""

from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
import torch

model_name = "{model}"
max_seq_length = 2048

# Load model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=max_seq_length,
    dtype=None,  # auto
    load_in_4bit=True,
)

# Add LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=3407,
)

# Load dataset
dataset = load_dataset("json", data_files="dataset.jsonl", split="train")

def format_prompt(example):
    text = f"### Instruction:\\n{{example['instruction']}}\\n\\n### Input:\\n{{example.get('input', '')}}\\n\\n### Response:\\n{{example['output']}}\\n<|endoftext|>"
    return {{"text": text}}

dataset = dataset.map(format_prompt)

# Training
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=5,
        max_steps=60,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        output_dir="outputs",
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
    ),
)

trainer.train()
model.save_pretrained("cascade-finetuned")
tokenizer.save_pretrained("cascade-finetuned")
print("Model saved to cascade-finetuned/")
'''.format(model=self.model_name)

        script_path = self.output_dir / "train.py"
        script_path.write_text(script)
        print_info(f"Training script saved to {script_path}")

    def _save_inference_script(self) -> None:
        script = '''"""Inference script for fine-tuned Cascade model."""

from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="cascade-finetuned",
    max_seq_length=2048,
    load_in_4bit=True,
)

FastLanguageModel.for_inference(model)

messages = [
    {{"role": "user", "content": "Write a Python function to reverse a string."}}
]
inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt")
outputs = model.generate(inputs, max_new_tokens=256, temperature=0.7)
print(tokenizer.batch_decode(outputs)[0])
'''
        script_path = self.output_dir / "inference.py"
        script_path.write_text(script)
        print_info(f"Inference script saved to {script_path}")
