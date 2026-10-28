"""Fábrica del modelo y resolución del proveedor configurado por entorno."""

import os

from agents import AsyncOpenAI, OpenAIChatCompletionsModel

BASE_URLS = {
    "openai": None,  # El SDK usa https://api.openai.com/v1 por defecto.
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}
MODELOS_POR_DEFECTO = {
    "openai": "gpt-4.1-mini",
    "gemini": "gemini-3.8-flash",
}
EMBEDDINGS_POR_DEFECTO = {
    "openai": "text-embedding-3-small",
    "gemini": "gemini-embedding-001",
}


def resolver_proveedor() -> tuple[str, str | None, str]:
    """Resuelve proveedor, base URL y clave usando PROVIDER_API_KEY como estándar.

    `OPENAI_API_KEY` se acepta solo como alias de compatibilidad cuando el
    proveedor es OpenAI.
    """
    provider = os.getenv("MODEL_PROVIDER", "openai")
    if provider not in ("openai", "gemini", "openai_compatible"):
        raise ValueError(f"MODEL_PROVIDER no soportado: {provider}")
    base_url = os.getenv("PROVIDER_BASE_URL") or BASE_URLS.get(provider)
    if provider == "openai_compatible" and not base_url:
        raise ValueError("PROVIDER_BASE_URL es obligatorio para openai_compatible")
    api_key = os.getenv("PROVIDER_API_KEY")
    if not api_key and provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Configura PROVIDER_API_KEY en el archivo .env")
    return provider, base_url, api_key


def modelo_embeddings() -> str:
    """Devuelve el modelo de embeddings según el proveedor activo."""
    provider = os.getenv("MODEL_PROVIDER", "openai")
    por_defecto = EMBEDDINGS_POR_DEFECTO.get(provider, EMBEDDINGS_POR_DEFECTO["openai"])
    return os.getenv("EMBEDDING_MODEL") or os.getenv("OPENAI_EMBEDDING_MODEL") or por_defecto


def build_model():
    """Construye el modelo configurado sin exponer credenciales en el código."""
    provider, base_url, api_key = resolver_proveedor()
    model_name = os.getenv("MODEL_NAME") or MODELOS_POR_DEFECTO.get(
        provider, MODELOS_POR_DEFECTO["openai"]
    )
    client = AsyncOpenAI(api_key=api_key, **({"base_url": base_url} if base_url else {}))
    return OpenAIChatCompletionsModel(model=model_name, openai_client=client)
