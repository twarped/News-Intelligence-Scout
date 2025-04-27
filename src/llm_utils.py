"""
llm_utils.py
------------
Utility functions for constructing and returning LLM clients for summarization and other tasks.
Supports deterministic configuration for reproducibility.
"""

def get_llm_client(api_key, model="gpt-4.1-nano", temperature=0, max_tokens=300):
    """
    Return a deterministic LLM client callable for OpenAI-compatible models.
    Args:
        api_key (str): OpenAI API key.
        model (str): Model name. Default: 'gpt-4.1-nano'.
        temperature (float): Sampling temperature. Default: 0.
        max_tokens (int): Max tokens for completion. Default: 300.
    Returns:
        Callable[[str], str]: Function that takes a prompt and returns a string completion.
    """
    if not api_key:
        return None
    import openai
    client = openai.OpenAI(api_key=api_key)
    def llm(prompt):
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=None
        )
        return response.choices[0].message.content
    return llm
