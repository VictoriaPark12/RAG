# pyright: reportGeneralTypeIssues=false
"""
😎😎 chat_service.py 서빙 관련 서비스

단순 채팅/대화형 LLM 인터페이스.

세션별 히스토리 관리, 요약, 토큰 절약 전략 등.
"""

from __future__ import annotations

import inspect
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

# NOTE:
# We intentionally store optional deps in `Any`-typed variables so MyPy does not
# treat imported class names as types that cannot be reassigned to `None`.
torch: Any = None
AutoModelForCausalLM: Any = None
AutoTokenizer: Any = None
BitsAndBytesConfig: Any = None

LoraConfig: Any = None
PeftModel: Any = None
get_peft_model: Any = None
prepare_model_for_kbit_training: Any = None

Dataset: Any = None
SFTConfig: Any = None
SFTTrainer: Any = None

try:
    import torch as _torch_runtime  # type: ignore
    from transformers import (  # type: ignore
        AutoModelForCausalLM as _AutoModelForCausalLM_runtime,
    )
    from transformers import (
        AutoTokenizer as _AutoTokenizer_runtime,
    )
    from transformers import (
        BitsAndBytesConfig as _BitsAndBytesConfig_runtime,
    )
except ModuleNotFoundError:  # pragma: no cover
    # 선택 의존성: 학습/로컬 추론용 환경에서만 필요할 수 있음.
    pass
else:
    torch = _torch_runtime
    AutoModelForCausalLM = _AutoModelForCausalLM_runtime
    AutoTokenizer = _AutoTokenizer_runtime
    BitsAndBytesConfig = _BitsAndBytesConfig_runtime

try:
    from peft import (  # type: ignore
        LoraConfig as _LoraConfig_runtime,
    )
    from peft import (
        PeftModel as _PeftModel_runtime,
    )
    from peft import (
        get_peft_model as _get_peft_model_runtime,
    )
    from peft import (
        prepare_model_for_kbit_training as _prepare_model_for_kbit_training_runtime,
    )
except ModuleNotFoundError:  # pragma: no cover
    pass
else:
    LoraConfig = _LoraConfig_runtime
    PeftModel = _PeftModel_runtime
    get_peft_model = _get_peft_model_runtime
    prepare_model_for_kbit_training = _prepare_model_for_kbit_training_runtime

try:
    from datasets import Dataset as _Dataset_runtime  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    pass
else:
    Dataset = _Dataset_runtime

try:
    # TRL exports changed across versions. Try a few known locations.
    try:
        from trl import SFTConfig as _SFTConfig_runtime  # type: ignore
    except Exception:  # pragma: no cover
        from trl.trainer.sft_config import (
            SFTConfig as _SFTConfig_runtime,  # type: ignore
        )

    try:
        from trl import SFTTrainer as _SFTTrainer_runtime  # type: ignore
    except Exception:  # pragma: no cover
        from trl.trainer.sft_trainer import (
            SFTTrainer as _SFTTrainer_runtime,  # type: ignore
        )
except ModuleNotFoundError:  # pragma: no cover
    pass
else:
    SFTConfig = _SFTConfig_runtime
    SFTTrainer = _SFTTrainer_runtime


def ensure_chat_deps() -> None:
    """Ensure optional chat/training dependencies are installed.

    Raises:
        ModuleNotFoundError: If required dependencies are missing.
    """
    if torch is None or AutoModelForCausalLM is None or AutoTokenizer is None:
        msg = (
            "chat_service 의존성이 설치되지 않았습니다. (torch/transformers)\n\n"
            "권장:\n"
            '  pip install "transformers>=4.40.0" "accelerate" "bitsandbytes" "peft" "trl" "datasets"\n'
        )
        raise ModuleNotFoundError(msg)


def get_optional_deps() -> dict[str, Any]:
    """Expose optional deps for debugging/introspection."""
    return {
        "torch": torch,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
        "BitsAndBytesConfig": BitsAndBytesConfig,
        "LoraConfig": LoraConfig,
        "PeftModel": PeftModel,
        "get_peft_model": get_peft_model,
        "prepare_model_for_kbit_training": prepare_model_for_kbit_training,
        "Dataset": Dataset,
        "SFTConfig": SFTConfig,
        "SFTTrainer": SFTTrainer,
    }


def ensure_qlora_deps() -> None:
    """Ensure QLoRA training dependencies are installed.

    Raises:
        ModuleNotFoundError: If required dependencies are missing.
    """
    ensure_chat_deps()
    missing: list[str] = []
    if (
        LoraConfig is None
        or get_peft_model is None
        or prepare_model_for_kbit_training is None
    ):
        missing.append("peft")
    if SFTTrainer is None or SFTConfig is None:
        missing.append("trl")
    if Dataset is None:
        missing.append("datasets")
    if missing:
        msg = (
            "QLoRA 학습 의존성이 설치되지 않았습니다.\n"
            f"누락: {', '.join(sorted(set(missing)))}\n\n"
            "권장:\n"
            '  pip install "peft" "trl" "datasets" "accelerate" "bitsandbytes"\n'
        )
        raise ModuleNotFoundError(msg)


@dataclass(frozen=True)
class QLoRAChatConfig:
    """Config for 4-bit QLoRA chat/inference."""

    base_model_path: str
    adapter_path: Optional[str] = None
    device_map: str = "auto"
    max_new_tokens: int = 256
    temperature: float = 0.0
    top_p: float = 1.0
    repetition_penalty: float = 1.05


@dataclass(frozen=True)
class QLoRATrainConfig:
    """Config for QLoRA SFT training."""

    base_model_path: str
    output_dir: str
    dataset_path: str
    text_field: str = "text"
    max_seq_length: int = 1024
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    num_train_epochs: int = 1
    logging_steps: int = 10
    save_steps: int = 200
    warmup_ratio: float = 0.03

    # LoRA hyperparams
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05


def _build_bnb_4bit_config() -> Any:
    """Create BitsAndBytesConfig for 4-bit QLoRA."""
    ensure_chat_deps()
    if BitsAndBytesConfig is None or torch is None:  # pragma: no cover
        raise ModuleNotFoundError("Missing transformers/bitsandbytes/torch")

    # GPU/CUDA 가용성 확인 후 로그
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU"
    print(f"[QLORA] 4-bit 양자화 설정 - Device: {device_name}, CUDA: {cuda_available}")

    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if cuda_available else torch.float16,
    )


def load_qlora_model_and_tokenizer(cfg: QLoRAChatConfig) -> tuple[Any, Any]:
    """Load a base model (4-bit) and optionally attach a LoRA adapter.

    Args:
        cfg: QLoRAChatConfig.

    Returns:
        (model, tokenizer)
    """
    ensure_chat_deps()
    if AutoTokenizer is None or AutoModelForCausalLM is None:
        raise ModuleNotFoundError("Missing transformers")

    # Fail fast for Windows path-like strings that don't exist.
    # This avoids HuggingFace Hub repo-id validation errors when a local path is wrong.
    base_path = Path(cfg.base_model_path)
    if (
        ":" in cfg.base_model_path
        or "\\" in cfg.base_model_path
        or "/" in cfg.base_model_path
    ) and not base_path.exists():
        raise FileNotFoundError(
            "베이스 모델 경로가 존재하지 않습니다.\n"
            f"- base_model_path: {cfg.base_model_path}\n\n"
            "로컬 모델 폴더 경로를 정확히 넣어주세요. 예:\n"
            r"  C:\Users\hi\Documents\devic\langchain\app\model\midm"
        )

    if cfg.adapter_path:
        adapter_path = Path(cfg.adapter_path)
        if (
            ":" in cfg.adapter_path
            or "\\" in cfg.adapter_path
            or "/" in cfg.adapter_path
        ) and not adapter_path.exists():
            raise FileNotFoundError(
                "QLoRA 어댑터 경로가 존재하지 않습니다.\n"
                f"- adapter_path: {cfg.adapter_path}\n\n"
                "학습 결과(output_dir) 폴더 경로를 정확히 넣어주세요."
            )

    tokenizer = AutoTokenizer.from_pretrained(
        cfg.base_model_path, use_fast=True, trust_remote_code=True
    )
    if (
        getattr(tokenizer, "pad_token_id", None) is None
        and getattr(tokenizer, "eos_token_id", None) is not None
    ):
        tokenizer.pad_token = tokenizer.eos_token

    quant_config = _build_bnb_4bit_config()
    print(f"[QLORA] 베이스 모델 로드 중: {cfg.base_model_path}")
    model: Any = AutoModelForCausalLM.from_pretrained(
        cfg.base_model_path,
        trust_remote_code=True,
        device_map=cfg.device_map,
        quantization_config=quant_config,
    )
    print(f"[QLORA] 모델 로드 완료 - Device map: {cfg.device_map}")

    if cfg.adapter_path:
        ensure_qlora_deps()
        if PeftModel is None:  # pragma: no cover
            raise ModuleNotFoundError("Missing peft")
        # Validate adapter folder contents for clearer errors than HFValidationError.
        adapter_dir = Path(cfg.adapter_path)
        adapter_config = adapter_dir / "adapter_config.json"
        adapter_weights_bin = adapter_dir / "adapter_model.bin"
        adapter_weights_safe = adapter_dir / "adapter_model.safetensors"
        if not adapter_config.exists():
            raise FileNotFoundError(
                "QLoRA 어댑터 폴더에 adapter_config.json 이 없습니다.\n"
                f"- adapter_path: {cfg.adapter_path}\n\n"
                "학습 output_dir(어댑터 저장 폴더)를 정확히 지정했는지 확인하세요."
            )
        if not (adapter_weights_bin.exists() or adapter_weights_safe.exists()):
            raise FileNotFoundError(
                "QLoRA 어댑터 폴더에 adapter_model.* 파일이 없습니다.\n"
                f"- adapter_path: {cfg.adapter_path}\n\n"
                "adapter_model.safetensors 또는 adapter_model.bin 이 필요합니다."
            )

        model = PeftModel.from_pretrained(model, cfg.adapter_path, is_trainable=False)

    model.eval()
    return model, tokenizer


@lru_cache(maxsize=2)
def load_cached_qlora(
    base_model_path: str,
    adapter_path: Optional[str],
    device_map: str,
) -> tuple[Any, Any]:
    """Load and cache (model, tokenizer) for repeated chat calls.

    This avoids re-loading weights on every request.
    """
    print(
        "[QLORA] load_cached_qlora: loading weights",
        {
            "base_model_path": base_model_path,
            "adapter_path": adapter_path,
            "device_map": device_map,
        },
    )
    cfg = QLoRAChatConfig(
        base_model_path=base_model_path,
        adapter_path=adapter_path,
        device_map=device_map,
    )
    return load_qlora_model_and_tokenizer(cfg)


def warmup_qlora_from_env() -> bool:
    """Warm up QLoRA model at service startup (optional).

    Returns:
        True if warmup executed (cache populated), False otherwise.
    """
    use_qlora = os.getenv("USE_QLORA", "0").lower() in {"1", "true", "yes"}
    base_model_path = os.getenv("QLORA_BASE_MODEL_PATH")
    adapter_path = os.getenv("QLORA_ADAPTER_PATH") or None
    device_map = os.getenv("QLORA_DEVICE_MAP", "auto")

    if not use_qlora:
        print("[QLORA] warmup skipped: USE_QLORA disabled")
        return False
    if not base_model_path:
        print("[QLORA] warmup skipped: QLORA_BASE_MODEL_PATH not set")
        return False

    print(
        "[QLORA] warmup starting",
        {
            "base_model_path": base_model_path,
            "adapter_path": adapter_path,
            "device_map": device_map,
        },
    )
    try:
        load_cached_qlora(base_model_path, adapter_path, device_map)
        print("[QLORA] warmup complete")
        return True
    except FileNotFoundError as e:
        print(f"[QLORA] warmup skipped: model path not found - {e}")
        return False
    except Exception as e:
        print(f"[QLORA] warmup failed: {e}")
        return False


def format_chat_prompt(messages: list[dict]) -> str:
    """Format a simple chat prompt from messages.

    Args:
        messages: [{"role": "user"|"assistant"|"system", "content": "..."}]

    Returns:
        Prompt string.
    """
    system = "너는 친절하고 유용한 한국어 어시스턴트야."
    parts: list[str] = [system]
    for msg in messages:
        role = (msg.get("role") or "").strip()
        content = (msg.get("content") or "").strip()
        if not role or not content:
            continue
        parts.append(f"{role}: {content}")
    parts.append("assistant:")
    return "\n".join(parts)


def _preview(text: str, *, max_len: int = 400) -> str:
    """Short preview for logs (avoid dumping huge prompts)."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


@torch.inference_mode() if torch is not None else (lambda f: f)  # type: ignore[misc]
def qlora_chat(
    cfg: QLoRAChatConfig,
    *,
    messages: list[dict],
    request_id: Optional[str] = None,
) -> str:
    """Run chat inference using a 4-bit QLoRA model (+ optional adapter).

    Args:
        cfg: QLoRAChatConfig.
        messages: List of chat messages.

    Returns:
        Generated answer string.
    """
    ensure_chat_deps()
    if torch is None:
        raise ModuleNotFoundError("Missing torch")

    t0 = time.perf_counter()
    model, tokenizer = load_cached_qlora(
        cfg.base_model_path, cfg.adapter_path, cfg.device_map
    )
    prompt = format_chat_prompt(messages)
    print(
        "[SERVICE] qlora_chat called",
        {
            "request_id": request_id,
            "base_model_path": cfg.base_model_path,
            "adapter_path": cfg.adapter_path,
            "device_map": cfg.device_map,
            "max_new_tokens": cfg.max_new_tokens,
            "prompt_preview": _preview(prompt),
        },
    )

    inputs = tokenizer(prompt, return_tensors="pt")
    # Some tokenizers return token_type_ids, but many causal LMs (e.g. Llama) don't use it.
    # `inputs` may be a transformers.BatchEncoding; it still supports `"key" in inputs` and `.pop()`.
    if "token_type_ids" in inputs:
        inputs.pop("token_type_ids", None)
    if hasattr(model, "device"):
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

    gen = model.generate(
        **inputs,
        max_new_tokens=cfg.max_new_tokens,
        do_sample=cfg.temperature > 0.0,
        temperature=max(cfg.temperature, 1e-6),
        top_p=cfg.top_p,
        repetition_penalty=cfg.repetition_penalty,
        pad_token_id=getattr(tokenizer, "pad_token_id", None),
        eos_token_id=getattr(tokenizer, "eos_token_id", None),
    )
    out = tokenizer.decode(gen[0], skip_special_tokens=True)

    # naive postprocess: keep the tail after last "assistant:"
    if "assistant:" in out:
        out = out.split("assistant:")[-1]
    answer = out.strip()
    dt_ms = int((time.perf_counter() - t0) * 1000)
    print(
        "[SERVICE] qlora_chat completed",
        {"request_id": request_id, "duration_ms": dt_ms, "answer_preview": _preview(answer, max_len=200)},
    )
    return answer


def rag_chat_with_qlora(
    *,
    base_model_path: str,
    adapter_path: Optional[str],
    question: str,
    context: str,
    conversation_history: list[dict],
    device_map: str = "auto",
    max_new_tokens: int = 256,
    request_id: Optional[str] = None,
) -> str:
    """Generate an answer using QLoRA model, given RAG context + history.

    This is a thin wrapper used by the RAG router to route generation through
    the QLoRA model loaded in this module.
    """
    cfg = QLoRAChatConfig(
        base_model_path=base_model_path,
        adapter_path=adapter_path,
        device_map=device_map,
        max_new_tokens=max_new_tokens,
        temperature=0.0,
    )

    system = (
        "너는 한국어로 답하는 유용한 어시스턴트야.\n"
        "아래 '참고 정보'가 주어지면 그 범위 안에서 답을 구성해.\n"
        "참고 정보가 부족하면 부족하다고 말하고, 필요한 추가 질문을 해.\n\n"
        f"[참고 정보]\n{context}\n"
    )

    messages: list[dict] = [{"role": "system", "content": system}]
    for msg in (conversation_history or [])[-10:]:
        role = msg.get("role")
        content = msg.get("content")
        if (
            role in {"user", "assistant"}
            and isinstance(content, str)
            and content.strip()
        ):
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": question})
    print(
        "[SERVICE] rag_chat_with_qlora",
        {"request_id": request_id, "question_preview": _preview(question, max_len=200)},
    )
    return qlora_chat(cfg, messages=messages, request_id=request_id)


def chat_with_qlora(
    *,
    base_model_path: str,
    adapter_path: Optional[str],
    message: str,
    conversation_history: list[dict],
    device_map: str = "auto",
    max_new_tokens: int = 256,
    request_id: Optional[str] = None,
) -> str:
    """General chat using QLoRA model (no retrieval context)."""
    cfg = QLoRAChatConfig(
        base_model_path=base_model_path,
        adapter_path=adapter_path,
        device_map=device_map,
        max_new_tokens=max_new_tokens,
        temperature=0.0,
    )

    messages: list[dict] = [
        {"role": "system", "content": "너는 친절하고 유용한 한국어 어시스턴트야."}
    ]
    for msg in (conversation_history or [])[-10:]:
        role = msg.get("role")
        content = msg.get("content")
        if (
            role in {"user", "assistant"}
            and isinstance(content, str)
            and content.strip()
        ):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    print(
        "[SERVICE] chat_with_qlora",
        {"request_id": request_id, "message_preview": _preview(message, max_len=200)},
    )
    return qlora_chat(cfg, messages=messages, request_id=request_id)


def _load_dataset_from_jsonl(dataset_path: str, *, text_field: str) -> Any:
    """Load dataset from jsonl.

    Each line should be a JSON object containing `text_field`.
    """
    ensure_qlora_deps()
    if Dataset is None:
        raise ModuleNotFoundError("Missing datasets")

    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        import json

        obj = json.loads(line)
        text = obj.get(text_field)
        if not isinstance(text, str) or not text.strip():
            continue
        rows.append({text_field: text})

    if len(rows) == 0:
        raise ValueError(
            f"Dataset is empty or missing field '{text_field}': {dataset_path}"
        )

    return Dataset.from_list(rows)


def train_qlora_sft(cfg: QLoRATrainConfig) -> str:
    """Train a QLoRA adapter using TRL SFTTrainer.

    Expected dataset format: JSONL with a `text` field (configurable).

    Args:
        cfg: Training config.

    Returns:
        Output directory containing the adapter.
    """
    ensure_qlora_deps()
    if AutoTokenizer is None or AutoModelForCausalLM is None:
        raise ModuleNotFoundError("Missing transformers")
    if torch is None:
        raise ModuleNotFoundError("Missing torch")
    if (
        LoraConfig is None
        or get_peft_model is None
        or prepare_model_for_kbit_training is None
    ):
        raise ModuleNotFoundError("Missing peft")
    if SFTTrainer is None or SFTConfig is None:
        raise ModuleNotFoundError("Missing trl")

    dataset = _load_dataset_from_jsonl(cfg.dataset_path, text_field=cfg.text_field)

    tokenizer = AutoTokenizer.from_pretrained(
        cfg.base_model_path, use_fast=True, trust_remote_code=True
    )
    if (
        getattr(tokenizer, "pad_token_id", None) is None
        and getattr(tokenizer, "eos_token_id", None) is not None
    ):
        tokenizer.pad_token = tokenizer.eos_token

    quant_config = _build_bnb_4bit_config()
    base_model = AutoModelForCausalLM.from_pretrained(
        cfg.base_model_path,
        trust_remote_code=True,
        device_map="auto",
        quantization_config=quant_config,
    )

    base_model = prepare_model_for_kbit_training(base_model)

    # Target modules: common for Llama-like models (may need adjustment per model)
    lora_config = LoraConfig(
        r=cfg.lora_r,
        lora_alpha=cfg.lora_alpha,
        lora_dropout=cfg.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    model = get_peft_model(base_model, lora_config)

    out_dir = Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # TRL's SFTConfig API also changes across versions. Build kwargs safely.
    sft_kwargs: dict[str, Any] = {
        "output_dir": str(out_dir),
        "per_device_train_batch_size": cfg.per_device_train_batch_size,
        "gradient_accumulation_steps": cfg.gradient_accumulation_steps,
        "num_train_epochs": cfg.num_train_epochs,
        "learning_rate": cfg.learning_rate,
        "logging_steps": cfg.logging_steps,
        "save_steps": cfg.save_steps,
        "warmup_ratio": cfg.warmup_ratio,
        "fp16": not torch.cuda.is_available(),
        "bf16": torch.cuda.is_available(),
        "report_to": [],  # disable wandb by default
    }
    sft_sig = inspect.signature(SFTConfig)  # type: ignore[arg-type]
    if "max_seq_length" in sft_sig.parameters:
        sft_kwargs["max_seq_length"] = cfg.max_seq_length
    elif "max_length" in sft_sig.parameters:
        sft_kwargs["max_length"] = cfg.max_seq_length

    sft_cfg = SFTConfig(**sft_kwargs)  # type: ignore[misc]

    # TRL's SFTTrainer API has changed across versions (e.g. tokenizer -> processing_class).
    # Use signature inspection to stay compatible.
    trainer_kwargs: dict[str, Any] = {
        "model": model,
        "train_dataset": dataset,
        "args": sft_cfg,
        "dataset_text_field": cfg.text_field,
    }
    sig = inspect.signature(SFTTrainer)  # type: ignore[arg-type]
    if "tokenizer" in sig.parameters:
        trainer_kwargs["tokenizer"] = tokenizer
    elif "processing_class" in sig.parameters:
        trainer_kwargs["processing_class"] = tokenizer

    trainer = SFTTrainer(**trainer_kwargs)  # type: ignore[misc]

    trainer.train()
    trainer.save_model(str(out_dir))
    return str(out_dir)
