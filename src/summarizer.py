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

import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
from nltk.tokenize import sent_tokenize



LLM_MODEL = "gpt-4.1-nano"
TARGET_COMPANY = "Red Pepper Software"

def build_llm_prompt(subject_company, target_company, rubric, instructions, content):
    if subject_company:
        return f"""
            We are evaluating a news article about '{subject_company}' and the business opportunity it may represent for '{target_company}'.\n
            Summarize the article in 120 words or less, showing how it's relevant to '{subject_company}'.
            If the article is not about or relevant to '{subject_company}', say so.\n
            {instructions}\n
            Article:\n
            {content}
        """
    else:
        return f"""
            Summarize the following news article in 120 words or less, focusing on its business relevance.\n
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
                    # Rubric for LLM scoring: explicitly listed for maintainers and for prompt clarity
                    rubric = """
                        Score from 0–100 using this additive rubric:

                        * 40 pts – Relevance to Red Pepper Software’s core services and vision:
                            - Qualtrics implementation/consulting or customer engagement strategy (10 pts)
                            - PDF or automated reporting systems (8 pts)
                            - Engineering services: API integrations, automation, or full-stack projects (8 pts)
                            - B2B/legacy system migration or modernization efforts (7 pts)
                            - Cloud-native architecture and cloud cost optimization solutions (7 pts)

                        * 20 pts – Sector urgency or expansion impacting Red Pepper's growth strategy:
                            - Digital transformation trends driving adoption of Red Pepper's offerings (7 pts)
                            - Increased IT budgets or expanded timelines, requiring additional Red Pepper services (7 pts)
                            - Expansion to new geographies/markets, creating demand for Red Pepper’s expertise (6 pts)

                        * 15 pts – Customer experience (CX) initiatives aligned with Red Pepper’s goals:
                            - Formal CX strategy/platform adoption leveraging Red Pepper's technology (5 pts)
                            - Adoption of survey, NPS, or feedback tooling that could be enhanced with Red Pepper’s solutions (5 pts)
                            - Investment in omnichannel or personalization initiatives that can be integrated with Red Pepper’s services (5 pts)

                        * 10 pts – Mergers & acquisitions requiring Red Pepper’s expertise:
                            - M&A involving enterprise software integrations where Red Pepper’s services are needed (5 pts)
                            - Spin-offs or divestitures with tech migration or reporting needs that match Red Pepper’s offerings (5 pts)

                        * 10 pts – Leadership changes or strategic shifts aligned with Red Pepper’s vision:
                            - New CTO/CIO/CDO/CXO with a focus on modernization, digital transformation, or automation (5 pts)
                            - Strategic organizational shifts that align with Red Pepper’s capabilities (5 pts)

                        * 5 pts – Compliance/regulatory urgency requiring Red Pepper’s technical input:
                            - Legal or reporting changes with tech implications that require Red Pepper’s systems or services (3 pts)
                            - Industry deadlines driving digital adoption, where Red Pepper can offer solutions (2 pts)

                        * 10 pts – Emerging technology drivers that Red Pepper can support or integrate:
                            - Adoption of AI agents, machine learning platforms, or AI-native apps in ways that align with Red Pepper’s offerings (5 pts)
                            - Investment in identity security, secrets governance, or compliance automation that Red Pepper can support (5 pts)                    """

                    # Clear deterministic instruction to LLM
                    instructions = f"""
                        Use the rubric below to assign a deterministic, additive score from 0 to 100.
                        Only assign points for clearly stated signals in the article.

                        In your summary:
                        - Do NOT mention {TARGET_COMPANY}.
                        
                        In your rationale:
                        - Focus on how {TARGET_COMPANY} can take advantage of the situation described in the article to help clients.
                        - Use language like "{TARGET_COMPANY} can use this opportunity to..." or "{TARGET_COMPANY} can help X by..." and focus on actionable steps.
                        - Mention the kinds of teams or companies that would benefit from the opportunity.
                        - Reference at least one capability or service that {TARGET_COMPANY} can offer to address this need.
                        - Avoid referencing the rubric items or point values directly in the rationale.

                        Respond in valid JSON with these keys:
                        - summary (≤120 words)
                        - score (integer 0–100)
                        - rationale (1 sentence, ≤20 words, actionable)

                        Rubric:
                        {rubric}
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
                    rationale = "LLM unavailable."
                    logging.error(f"OpenAI error during summarization: {e}")
            if summary is None:
                summary = heuristic_summary(content)
                score = 0
                rationale = "LLM unavailable."
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


