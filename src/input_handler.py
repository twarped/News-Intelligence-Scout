"""
input_handler.py
----------------
Handles extraction of company names from URLs or search terms for use in news retrieval and summarization.
Provides LLM-based and heuristic extraction methods. Used as the first step in the News Intelligence Scout pipeline.
"""

import os
import re
import logging
import requests
from bs4 import BeautifulSoup
import whois
from urllib.parse import urlparse
import json


USE_LLM_COMPANY_NAME_EXTRACTION = True

def extract_subject_company(url: str) -> str:
    """
    Extract the company name from a website URL using metadata, WHOIS, or heuristics.
    Deterministic: same input yields same output.
    Logs all extraction attempts and sources used.
    """
    logging.info(f"[CompanyName] Starting legacy extraction for URL: {url}")
    # 1. Try structured metadata (Open Graph, meta tags)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        }
        resp = requests.get(url, timeout=15, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        logging.debug(f"[CompanyName] Parsed HTML for {url}")
        # Try Open Graph site_name
        og_site_name = soup.find('meta', property='og:site_name')
        if og_site_name and og_site_name.get('content'):
            name = og_site_name['content'].strip()
            if name:
                logging.info(f"[CompanyName] Extracted from og:site_name: {name}")
                return name
        # Try <title>
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            if title:
                logging.info(f"Extracted from <title>: {title}")
                return title
        # Try meta[name=application-name]
        app_name = soup.find('meta', attrs={'name': 'application-name'})
        if app_name and app_name.get('content'):
            name = app_name['content'].strip()
            if name:
                logging.info(f"Extracted from application-name meta: {name}")
                return name
    except Exception as e:
        logging.info(f"Metadata extraction failed: {e}")
    # 2. Fallback to WHOIS
    try:
        domain = urlparse(url).netloc
        domain = re.sub(r'^www\.', '', domain)
        w = whois.whois(domain)
        # Prefer organization, fallback to registrant
        org = w.get('org') or w.get('organization')
        if org and isinstance(org, str):
            org = org.strip()
            if org:
                logging.info(f"Extracted from WHOIS org: {org}")
                return org
        # Sometimes WHOIS returns a list
        if isinstance(org, list) and org:
            org = org[0].strip()
            if org:
                logging.info(f"Extracted from WHOIS org list: {org}")
                return org
    except Exception as e:
        logging.info(f"WHOIS extraction failed: {e}")
    # 3. Heuristic fallback: use domain
    if not domain:
        domain = urlparse(url).netloc
    # Remove www. and TLD
    base = re.sub(r'^www\.', '', domain)
    base = base.split('.')[0]
    subject_company = base.replace('-', ' ').replace('_', ' ').title()
    logging.info(f"Extracted heuristically: {subject_company}")
    return subject_company

def extract_subject_company_llm(url: str, llm_client=None) -> dict:
    """
    Extract the company name using LLM and structured metadata from the target URL.
    Returns dict: {"inferred_name": str, "confidence": float, "explanation": str}
    Falls back to extract_subject_company if confidence < 0.3.
    Logs all steps, metadata, prompt, LLM response, parsed result, and fallback reason.
    """
    logging.info(f"[CompanyName][LLM] Starting AI-powered extraction for URL: {url}")
    # Collect metadata
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        resp = requests.get(url, timeout=15, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        meta_desc = (soup.find('meta', attrs={'name': 'description'}) or {}).get('content') if soup.find('meta', attrs={'name': 'description'}) else None
        og_title = (soup.find('meta', property='og:title') or {}).get('content') if soup.find('meta', property='og:title') else None
        og_site_name = (soup.find('meta', property='og:site_name') or {}).get('content') if soup.find('meta', property='og:site_name') else None
        h1 = soup.find('h1').get_text(strip=True) if soup.find('h1') else None
        logging.info(f"[CompanyName][LLM] Collected metadata: title='{title}', meta_description='{meta_desc}', og_title='{og_title}', og_site_name='{og_site_name}', h1='{h1}'")
    except Exception as e:
        logging.info(f"[CompanyName][LLM] Metadata extraction failed: {e}")
        title = meta_desc = og_title = og_site_name = h1 = None
    try:
        domain = urlparse(url).netloc
        domain = re.sub(r'^www\\.', '', domain)
        w = whois.whois(domain)
        whois_org = w.get('org') or w.get('organization')
        if isinstance(whois_org, list):
            whois_org = whois_org[0] if whois_org else None
        logging.info(f"[CompanyName][LLM] WHOIS org: '{whois_org}', domain: '{domain}'")
    except Exception as e:
        logging.info(f"[CompanyName][LLM] WHOIS extraction failed: {e}")
        whois_org = None
        domain = urlparse(url).netloc
    # Build metadata dict
    metadata = {
        "title": title,
        "meta_description": meta_desc,
        "og_title": og_title,
        "og_site_name": og_site_name,
        "h1": h1,
        "whois_org": whois_org,
        "domain": domain,
    }
    logging.info(f"[CompanyName][LLM] Metadata dict for LLM: {json.dumps(metadata, ensure_ascii=False)}")
    # LLM prompt
    prompt = f"""
        You are identifying the correct **brand name** associated with the following website or article. 
        This should be the name **most prominently used by the public and in branding**, including headlines and user interfaces. 
        Do NOT default to the parent company unless the brand name is unclear or not independently recognized. 
        Avoid legal suffixes like 'Inc.' or 'LLC' unless part of the public-facing brand.\n
        Respond in JSON format:\n
        - 'inferred_name': a string\n
        - 'confidence': a float from 0.0 to 1.0\n
        - 'explanation': a brief rationale (1-2 sentences)\n
        Only include the requested keys in your response. Do not add any extra text or commentary.\n
        METADATA: {json.dumps(metadata, ensure_ascii=False)}
    """
    logging.info(f"[CompanyName][LLM] Prompt sent to LLM:\n{prompt}")
    # Call LLM
    llm_response = None
    if llm_client:
        llm_response = llm_client(prompt)
        logging.info(f"[CompanyName][LLM] Raw LLM response: {llm_response}")
    else:
        raise RuntimeError("No LLM client provided for company name extraction.")
    try:
        result = json.loads(llm_response)
        inferred_name = result.get("inferred_name")
        confidence = float(result.get("confidence", 0.0))
        explanation = result.get("explanation", "")
        logging.info(f"[CompanyName][LLM] Parsed LLM result: name='{inferred_name}', confidence={confidence}, explanation='{explanation}'")
        if confidence < 0.3:
            fallback = extract_subject_company(url)
            logging.info(f"[CompanyName][LLM] Fallback to legacy extractor due to low LLM confidence ({confidence}).")
            return {"inferred_name": fallback, "confidence": 0.0, "explanation": "Fallback to heuristic extractor due to low LLM confidence."}
        return {"inferred_name": inferred_name, "confidence": confidence, "explanation": explanation}
    except Exception as e:
        logging.info(f"[CompanyName][LLM] LLM JSON parsing failed: {e}")
        fallback = extract_subject_company(url)
        logging.info(f"[CompanyName][LLM] Fallback to legacy extractor due to LLM failure.")
        return {"inferred_name": fallback, "confidence": 0.0, "explanation": "Fallback to heuristic extractor due to LLM failure."}
