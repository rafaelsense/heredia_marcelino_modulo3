"""Fábrica del modelo usado por los componentes generativos del agente."""

import os

from agents import AsyncOpenAI, OpenAIChatCompletionsModel

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def build_model():
    """Construye el modelo configurado sin exponer credenciales en el código."""
    provider = os.getenv("MODEL_PROVIDER", "openai")
    model_name = os.getenv("MODEL_NAME", "gpt-4.1-mini")
    if provider == "openai":
        return model_name
    if provider in ("openai_compatible", "gemini"):
        base_url = os.getenv(
            "PROVIDER_BASE_URL",
            GEMINI_BASE_URL if provider == "gemini" else None,
        )
        if not base_url:
            raise ValueError("PROVIDER_BASE_URL es obligatorio para openai_compatible")
        client = AsyncOpenAI(base_url=base_url, api_key=os.environ["PROVIDER_API_KEY"])
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)
    raise ValueError(f"MODEL_PROVIDER no soportado: {provider}")
