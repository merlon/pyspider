import time
import json
import re

from typing import NamedTuple, Optional, Callable, Any, Dict
from dateutil.parser import parse
from dateutil.parser._parser import ParserError  # type: ignore


def parsedate(txt: str) -> Optional[float]:
    try:
        return parse(txt, fuzzy=True).timestamp()
    except ParserError:
        return None
    return None


# https://github.com/merlon/merlon/blob/master/protos/messages/src/cloud/article.proto
SOURCE_TYPES = [
    "UNDEFINED",
    "REGULATORY_ENFORCEMENT",
    "LAW_ENFORCEMENT",
    "JUDICIARY_COURT_RECORDS",
    "NONGOV_ORG",
]

DOCUMENT_TYPES = [
    "UNKNOWN",
    "NEWS",
    "PRESS_RELEASE",
    "COMMENT",
    "ALERT",
    "LITIGATION",
    "OTHER",
]

IMPORTANCE = ["LOW", "MEDIUM", "HIGH"]


def validate_institution_name(result: dict) -> str:
    iname = result.get("institution_name", None) or result.get("name", None)
    if iname is None or not iname:
        raise ValueError("Institution name missing")
    return iname.strip()


def validate_short_institution_name(result: dict) -> str:
    sn = result.get("short_institution_name", None) or\
            result.get("short_name", None) or\
            result.get("short", None)
    if sn is None or not sn:
        raise ValueError("Short institution name missing")
    return sn.strip()


def validate_source_type(result: dict) -> str:
    st = result.get("source_type", None)
    if st is None or st not in SOURCE_TYPES:
        # TODO: monitor missing source type?
        return SOURCE_TYPES[0]
    return st


def validate_document_type(result: dict) -> str:
    dt = result.get("document_type", None)
    if dt is None or dt not in DOCUMENT_TYPES:
        # TODO: monitor missing document type?
        return DOCUMENT_TYPES[0]
    return dt


def validate_importance(result: dict) -> str:
    imp = result.get("importance", "LOW")
    return "LOW" if imp not in IMPORTANCE else imp


def validate_published(result: dict) -> float:
    pub = result.get("published", None)
    now = time.time()  #  timezone?
    # TODO: monitor fallback to crawl timestamp
    if pub is None:
        return now
    elif type(pub) == str:
        guess = parsedate(pub)
        if guess is None:
            return now
        elif type(guess) == float:
            return guess
        else:
            return now
    elif type(pub) == float and pub > 0.0:
        return pub
    else:
        raise ValueError("Published time should be a timestamp (float)")


def validate_title(result: dict) -> str:
    # TODO: monitor empty title
    return result.get("title", "").strip()


def validate_body(result: dict) -> Optional[str]:
    # TODO: monitor empty body
    b = result.get("body", None)
    if b is None:
        raise ValueError("Missing body in response")
    b = b.strip()
    if not b:
        raise ValueError("Empty body")
    return b


def validate_lang(result: dict) -> str:
    lang = result.get("expected_language_code", None) or\
            result.get("lang_code", None) or\
            result.get("lang", None) or\
            result.get("language", None)
    simple_re = re.compile("[a-z][a-z]")
    locale_re = re.compile("[a-z][a-z]-[A-Z][A-Z]")
    if lang is None:
        raise ValueError("Language code not provided")
    elif simple_re.match(lang):
        return lang
    elif locale_re.match(lang):
        return lang
    else:
        raise ValueError("Wrong language code value")


def validate_jurisdiction(result: dict) -> str:
    jur = result.get("jurisdiction", None) or result.get("country", None)
    if jur is None:
        raise ValueError("Jurisdiction is not defined")
    iso3166_re = re.compile("[A-Z][A-Z]")
    jur = jur.strip()
    if not jur:
        raise ValueError("Jurisdiction is empty")
    elif not iso3166_re.match(jur):
        raise ValueError("Wrong ISO 3166 code")
    return jur


def validate_jurisdiction_state(result: dict) -> Optional[str]:
    jurs = result.get("jurisdiction_state", None) or result.get("state", None)
    if jurs is None or not jurs.strip():
        return None
    return jurs.strip()


def validate_jurisdiction_municipality(result: dict) -> Optional[str]:
    jurm = result.get("jurisdiction_municipality", None) or\
            result.get("municipality", None) or\
            result.get("town", None)
    if jurm is None or not jurm.strip():
        return None
    return jurm.strip()


def validate_response(res: dict) -> dict:
    "Used as a decorator in scraper scripts. Ensures the proper JSON."

    return {
        "published": validate_published(res),
        "title": validate_title(res),
        "body": validate_body(res),
        "name": validate_institution_name(res),
        "short_name": validate_short_institution_name(res),
        "source_type": validate_source_type(res),
        "document_type": validate_document_type(res),
        "lang_code": validate_lang(res),
        "jurisdiction": validate_jurisdiction(res),
        "jurisdiction_state": validate_jurisdiction_state(res),
        "jurisdiction_municipality": validate_jurisdiction_municipality(res),
        "importance": validate_importance(res),
    }


def convert(task: dict, result: dict, timestamp: float) -> dict:
    "Takes result and prepares JSON to be stored in GCS"

    return {
        **result,
        "id": task["taskid"],
        "url": task["url"],
        "version": timestamp,
        "crawled": timestamp,
    }
