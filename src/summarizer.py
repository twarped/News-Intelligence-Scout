"""
summarizer.py
-------------
Handles summarization and opportunity scoring of news articles using LLMs (e.g., OpenAI) and deterministic heuristics.
Provides the core business logic for ranking and evaluating articles for Red Pepper Software.
"""

import os
import logging
import openai
from typing import Generator, Optional, Callable, TypedDict
from dotenv import load_dotenv
load_dotenv()

_RUBRIC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'rubric.txt'))
try:
    with open(_RUBRIC_PATH, 'r') as f:
        RUBRIC_TEXT = f.read()
except FileNotFoundError:
    RUBRIC_TEXT = ""

import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
from nltk.tokenize import sent_tokenize



LLM_MODEL = "gpt-4.1-nano"
TARGET_COMPANY = "Red Pepper Software"

def build_llm_prompt(subject_company, target_company, rubric, instructions, content):
    return f"""
        We are evaluating a news article about '{subject_company}' and the business opportunity it may represent for '{target_company}'.\n
        Summarize the article in 120 words or less, showing how it's relevant to '{subject_company}'.
        If the article is not about or relevant to '{subject_company}', say so.\n
        {instructions}\n
        Article:\n
        {content}
    """

class ArticleDict(TypedDict, total=False):
    title: str
    extracted_text: str
    content: str
    summary: str
    score: int
    rationale: str
    published_at: str
    url: str
    rank: int


def summarize_articles(
    articles: list[ArticleDict],
    subject_company: Optional[str] = None,
    summarizer_fn: Optional[Callable[[ArticleDict], str]] = None,
    progress_callback: Optional[Callable[[int, int, ArticleDict, str, int, str], None]] = None
) -> Generator[ArticleDict, None, None]:
    """
    Summarize and score each article using OpenAI LLM if available, else fallback to heuristic.
    LLM returns JSON: {"summary": str, "score": int, "rationale": str}.
    Fallback: summary is heuristic, score=0, rationale="LLM unavailable.".
    Each result includes all original article keys plus summary, score, rationale.
    Deterministic: temperature=0. Max 500 chars per summary.
    """
    import json
    api_key = os.getenv("OPENAI_API_KEY")
    use_llm = api_key and openai is not None
    client = None
    if use_llm:
        try:
            client = openai.OpenAI(api_key=api_key)
        except openai.OpenAIError:
            use_llm = False
    total = len(articles)
    for idx, article in enumerate(articles):
        content = article.get('extracted_text') or article.get('content') or ''
        summary = None
        score = 0
        rationale = "LLM unavailable."
        if summarizer_fn is not None:
            summary = summarizer_fn(article)
        else:
            if use_llm:
                try:
                    # Clear deterministic instruction to LLM, and inline subject_company in rubric
                    rubric_text = RUBRIC_TEXT.replace("{subject_company}", subject_company)
                    instructions = f"""
                        Use the rubric below to assign a deterministic, additive score from 0 to 100.
                        Only assign points for clearly stated signals in the article.

                        In your summary:
                        - Do NOT mention {TARGET_COMPANY}.
                        - Do NOT talk about {TARGET_COMPANY}.
                        - Only summarize the article.
                        - Do NOT add your own commentary.
                        - Is '{subject_company}' in the article
                        
                        In your rationale:
                        - Focus on how {TARGET_COMPANY} can take advantage of the situation described in the article to help clients.
                        - Use language like "{TARGET_COMPANY} can use this opportunity to..." or "{TARGET_COMPANY} can help X by..." and focus on actionable steps.
                        - Mention the kinds of teams or companies that would benefit from the opportunity.
                        - Reference at least one capability or service that {TARGET_COMPANY} can offer to address this need.
                        - Avoid referencing the rubric items or point values directly in the rationale.

                        Respond in valid JSON with these keys:
                        - summary (≤120 words)
                        - score (integer)
                        - rationale (1 sentence, ≤20 words, why the score)

                        Rubric:
                        {rubric_text}
                    """

                    # Then for your final prompt:
                    if subject_company:
                        prompt = f"""
                            We are evaluating a news article about '{subject_company}' and the business opportunity it may represent for '{TARGET_COMPANY}'.\n
                            Summarize the article in 120 words or less, showing how it's relevant to '{subject_company}'.
                            If the article is not about or relevant to '{subject_company}', say so.\n
                            {instructions}\n
                            Article:\n
                            {content}
                        """
                    else:
                        prompt = f"""
                            We are evaluating this news article about a company, and the business opportunity it may represent for '{TARGET_COMPANY}'.\n
                            Summarize this article in 120 words or less.
                            {instructions}\n
                            Article:\n
                            {content}
                        """
                    resp = client.chat.completions.create(
                        model=LLM_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                        max_tokens=4096,
                    )
                    llm_json = resp.choices[0].message.content.strip()
                    try:
                        llm_result = json.loads(llm_json)
                        summary = llm_result.get("summary", "")
                        score = llm_result.get("score", 0)
                        rationale = llm_result.get("rationale", "")
                    except json.JSONDecodeError as e:
                        # Try to fix a common case: missing closing bracket
                        fixed_json = llm_json.strip()
                        if not fixed_json.endswith('}'):  # only try if clearly missing
                            fixed_json = fixed_json + '}'
                        try:
                            llm_result = json.loads(fixed_json)
                            summary = llm_result.get("summary", "")
                            score = llm_result.get("score", 0)
                            rationale = llm_result.get("rationale", "")
                            logging.warning(f"LLM JSON fixed by appending closing bracket: {fixed_json}")
                        except json.JSONDecodeError as e2:
                            # Try to escape unescaped double quotes inside string values
                            import re
                            def escape_inner_quotes(json_str):
                                # Only escape quotes inside values for summary, rationale, and title keys
                                def replacer(match):
                                    key = match.group(1)
                                    value = match.group(2)
                                    # Escape only unescaped quotes (not already preceded by backslash)
                                    value_escaped = re.sub(r'(?<!\\)"', r'\\"', value)
                                    return f'"{key}": "{value_escaped}"'
                                # Regex: match "key": "value"
                                pattern = r'"(summary|rationale|title)":\s*"(.*?)"(?=,|\n|})'
                                return re.sub(pattern, replacer, json_str, flags=re.DOTALL)
                            escaped_json = escape_inner_quotes(fixed_json)
                            try:
                                llm_result = json.loads(escaped_json)
                                summary = llm_result.get("summary", "")
                                score = llm_result.get("score", 0)
                                rationale = llm_result.get("rationale", "")
                                logging.warning(f"LLM JSON fixed by escaping inner quotes: {escaped_json}")
                            except json.JSONDecodeError as e3:
                                summary = None
                                score = 0
                                rationale = "LLM unavailable (invalid JSON)."
                                logging.warning(f"LLM returned invalid JSON (even after all fixes): {llm_json} | Error: {e3}")
                except openai.OpenAIError as e:
                    summary = None
                    score = 0
                    logging.error(f"OpenAI error during summarization: {e}")
            if summary is None:
                summary = heuristic_summary(content)
                score = 0
                rationale = "LLM sent bad response, falling back to heuristic summary."
        result = dict(article)
        result["summary"] = summary if summary is not None else ""
        result["score"] = score
        result["rationale"] = rationale
        if progress_callback:
            progress_callback(idx+1, total, article, summary, score, rationale)
        yield result


def heuristic_summary(content: str) -> str:
    """
    Generate a heuristic summary from the content using NLTK sentence tokenization if available.
    Returns up to 3 sentences or 500 characters.
    Warn if NLTK is not available.
    """
    if not content:
        return "No content available."
    if nltk and sent_tokenize:
        return ' '.join(sent_tokenize(content, language='english')[:3])[:500]
    logging.warning("NLTK not available, falling back to naive string slicing for summary.")
    return content[:500]
