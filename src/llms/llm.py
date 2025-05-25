from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.rate_limiters import InMemoryRateLimiter

load_dotenv()

def create_llm_model(
    model: str,
    temperature: float = 0.0,
    **kwargs,
) -> ChatOpenAI | ChatGoogleGenerativeAI:
    """
    Create a ChatOpenAI instance with the specified configuration.

    Args:
        model: Name of the OpenAI model.
        temperature: Sampling temperature.
        **kwargs: Additional parameters to pass to the LLM.

    Returns:
        A configured ChatOpenAI | ChatGoogleGenerativeAI instance.
    """
    
    rate_limiter_openai = InMemoryRateLimiter(
        requests_per_second=0.5, check_every_n_seconds=0.1, max_bucket_size=1
    )

    rate_limiter_gemini = InMemoryRateLimiter(
        requests_per_second=0.4, check_every_n_seconds=0.1, max_bucket_size=1
    )
    
    if model in {"gpt-4o", "gpt-4o-mini"}:
        llm_kwargs = {"model": model, "temperature": temperature, **kwargs}
        return ChatOpenAI(**llm_kwargs)
    elif model in {"o3-mini", "o4-mini"}:
        llm_kwargs = {"model": model, "reasoning_effort": "medium", **kwargs}
        return ChatOpenAI(**llm_kwargs)
    elif model == "gpt-4.1-mini":
        llm = init_chat_model(
            "openai:gpt-4.1-mini",
            temperature=0,
            max_retries=3,
            rate_limiter=rate_limiter_openai,
        )
        return llm
    elif model == "gemini-2.0-flash-lite":
        llm = ChatGoogleGenerativeAI(
            temperature=0,
            model="gemini-2.0-flash-lite",
            max_tokens=None,
            timeout=60,
            max_retries=5,
            rate_limiter=rate_limiter_gemini,
        )
        return llm
    else:
        raise ValueError(f"Unsupported model: {model}")
