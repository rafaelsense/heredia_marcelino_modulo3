"""Fábrica del modelo usado por los componentes generativos del agente."""

import os

from agents import AsyncOpenAI, OpenAIChatCompletionsModel


def build_model():
    """Construye el modelo configurado sin exponer credenciales en el código."""
    provider = os.getenv("MODEL_PROVIDER", "openai")
    model_name = os.getenv("MODEL_NAME", "gpt-4.1-mini")
    if provider == "openai":
        return model_name
    if provider == "openai_compatible":
        base_url = os.environ["PROVIDER_BASE_URL"]
        api_key = os.environ["PROVIDER_API_KEY"]
        client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)
    raise ValueError(f"MODEL_PROVIDER no soportado: {provider}")
