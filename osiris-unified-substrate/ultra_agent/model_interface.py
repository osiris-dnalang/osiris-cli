"""Model interface — abstraction layer for real vs simulated inference.

Every agent routes generation through this interface.  When a real
model (transformers, vLLM, API) is attached, calls go through it.
When no model is present the system operates in *simulation mode*
and every output is explicitly tagged.

This is the single point where latency, token counts, and inference
metadata are recorded, satisfying the scientific-defensibility
requirement that every output carries provenance.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class InferenceResult:
    """Wraps every generation with provenance metadata."""
    text: str
    mode: str                      # "model" | "simulation"
    latency_ms: float              # wall-clock time
    tokens_generated: int          # estimated token count
    tokens_prompt: int             # estimated prompt token count
    model_id: str                  # e.g. "meta-llama/Llama-3-8B" or "simulation"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "mode": self.mode,
            "latency_ms": round(self.latency_ms, 2),
            "tokens_generated": self.tokens_generated,
            "tokens_prompt": self.tokens_prompt,
            "model_id": self.model_id,
            "metadata": self.metadata,
        }


def _estimate_tokens(text: str) -> int:
    """Rough whitespace-based token estimate (≈ 0.75× word count for English)."""
    return max(1, int(len(text.split()) * 1.3))


class ModelInterface:
    """Unified generation interface with simulation fallback.

    Attach a real model via ``attach_model`` or leave unattached
    to operate in simulation mode.  Every call returns an
    ``InferenceResult`` with mode, latency, and token counts.
    """

    def __init__(self) -> None:
        self._model: Optional[Any] = None
        self._tokenizer: Optional[Any] = None
        self._model_id: str = "simulation"
        self._generate_fn: Optional[Callable[..., str]] = None

    @property
    def simulation_mode(self) -> bool:
        return self._model is None and self._generate_fn is None

    @property
    def model_id(self) -> str:
        return self._model_id

    # ---- attachment API ----

    def attach_model(
        self,
        model: Any,
        tokenizer: Any,
        model_id: str = "custom",
    ) -> None:
        """Attach a HuggingFace-compatible model + tokenizer."""
        self._model = model
        self._tokenizer = tokenizer
        self._model_id = model_id

    def attach_generate_fn(
        self,
        fn: Callable[[str], str],
        model_id: str = "custom-fn",
    ) -> None:
        """Attach an arbitrary generation function (API wrapper, etc.)."""
        self._generate_fn = fn
        self._model_id = model_id

    def detach(self) -> None:
        """Return to simulation mode."""
        self._model = None
        self._tokenizer = None
        self._generate_fn = None
        self._model_id = "simulation"

    # ---- generation ----

    def generate(
        self,
        prompt: str,
        *,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        simulation_output: str = "",
    ) -> InferenceResult:
        """Generate text, using real model if attached, else simulation.

        Parameters
        ----------
        prompt : str
            The generation prompt.
        max_new_tokens : int
            Maximum tokens to generate (model mode).
        temperature : float
            Sampling temperature (model mode).
        simulation_output : str
            Deterministic output used when no model is attached.
            Callers *must* provide this so simulation results are
            explicitly constructed, not silently fabricated.
        """
        prompt_tokens = _estimate_tokens(prompt)
        t0 = time.perf_counter()

        if self._generate_fn is not None:
            # Custom function path (API, vLLM, etc.)
            text = self._generate_fn(prompt)
            latency = (time.perf_counter() - t0) * 1000
            gen_tokens = _estimate_tokens(text)
            return InferenceResult(
                text=text,
                mode="model",
                latency_ms=latency,
                tokens_generated=gen_tokens,
                tokens_prompt=prompt_tokens,
                model_id=self._model_id,
            )

        if self._model is not None and self._tokenizer is not None:
            # HuggingFace path
            inputs = self._tokenizer(prompt, return_tensors="pt")
            prompt_tokens = inputs["input_ids"].shape[-1]
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
            )
            text = self._tokenizer.decode(
                outputs[0][prompt_tokens:], skip_special_tokens=True
            )
            latency = (time.perf_counter() - t0) * 1000
            gen_tokens = outputs.shape[-1] - prompt_tokens
            return InferenceResult(
                text=text,
                mode="model",
                latency_ms=latency,
                tokens_generated=int(gen_tokens),
                tokens_prompt=int(prompt_tokens),
                model_id=self._model_id,
            )

        # Simulation mode
        latency = (time.perf_counter() - t0) * 1000
        gen_tokens = _estimate_tokens(simulation_output)
        return InferenceResult(
            text=simulation_output,
            mode="simulation",
            latency_ms=latency,
            tokens_generated=gen_tokens,
            tokens_prompt=prompt_tokens,
            model_id="simulation",
            metadata={"warning": "No model attached — output is heuristic"},
        )


# Module-level singleton so all agents share one interface
_shared: Optional[ModelInterface] = None


def get_model_interface() -> ModelInterface:
    """Return the shared model interface singleton."""
    global _shared
    if _shared is None:
        _shared = ModelInterface()
    return _shared
