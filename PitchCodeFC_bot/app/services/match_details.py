import re
from urllib.parse import urlsplit

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

from .match_search import parse_flashscore_match_url


class MatchDetailsError(Exception):
    """Base exception for match-detail retrieval."""


class MatchPageUnavailableError(MatchDetailsError):
    """The match page could not be loaded or recognised."""


# Flashscore's page structure can change. Keeping selector alternatives here
# makes future maintenance easier.
HOME_TEAM_SELECTORS = (
    ".duelParticipant__home .participant__participantName",
    '[data-testid="wcl-scores-overline-03"]',
    '[data-testid*="participantName-home"]',
)

AWAY_TEAM_SELECTORS = (
    ".duelParticipant__away .participant__participantName",
    '[data-testid="wcl-scores-overline-04"]',
    '[data-testid*="participantName-away"]',
)

# Current Flashscore pages often expose both scores in one element:
# .detailScore__wrapper, with text such as "0\\n-\\n3".
SCORE_WRAPPER_SELECTORS = (
    ".detailScore__wrapper",
    ".duelParticipant__score",
)

STATUS_SELECTORS = (
    ".detailScore__status",
    '[data-testid="wcl-matchStatus"]',
    ".fixedHeaderDuel__detailStatus",
)


def _first_text(driver, selectors):
    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for element in elements:
            text = element.text.strip()
            if text:
                return text
    return None


def _normalise_status(value):
    return " ".join((value or "").lower().split())


def _classify_status(raw_status):
    """
    Map Flashscore's displayed status into a stable internal status.

    The original text is preserved separately in the returned dictionary.
    """
    status = _normalise_status(raw_status)

    if not status:
        return "unknown"

    finished_terms = (
        "finished", "terminado", "fim do jogo", "após prolongamento",
        "after extra time", "after penalties", "após penáltis",
    )
    if any(term in status for term in finished_terms):
        return "finished"

    half_time_terms = (
        "half-time", "half time", "intervalo", "intervalo do jogo",
    )
    if any(term in status for term in half_time_terms):
        return "half_time"

    penalty_terms = ("penalties", "penáltis", "penaltis")
    if any(term in status for term in penalty_terms):
        return "penalties"

    extra_time_terms = (
        "extra time", "prolongamento", "aet",
    )
    if any(term in status for term in extra_time_terms):
        return "extra_time"

    second_half_terms = (
        "2nd half", "second half", "2º tempo", "2o tempo",
        "segunda parte", "2ª parte",
    )
    if any(term in status for term in second_half_terms):
        return "second_half"

    first_half_terms = (
        "1st half", "first half", "1º tempo", "1o tempo",
        "primeira parte", "1ª parte",
    )
    if any(term in status for term in first_half_terms):
        return "first_half"

    not_started_terms = (
        "not started", "scheduled", "a iniciar", "não começou",
        "nao comecou", "adiado", "postponed", "cancelled",
        "cancelado",
    )
    if any(term in status for term in not_started_terms):
        return "not_started"

    # If a live clock is shown, infer the half from the minute.
    minute = _parse_minute(raw_status)
    if minute is not None:
        return "second_half" if minute >= 46 else "first_half"

    return "unknown"


def _parse_minute(raw_status):
    """
    Parse a displayed match clock into elapsed match minute.

    Handles examples such as:
      80'       -> 80
      45+2'     -> 47
      90+5'     -> 95
      2nd Half 80:12 -> 80

    Returns None when no reliable minute is present.
    """
    if not raw_status:
        return None

    text = raw_status.strip()

    # Prefer explicit minute notation, including stoppage time.
    match = re.search(
        r"(?<!\d)(\d{1,3})\s*\+\s*(\d{1,2})\s*['’′]?",
        text
    )
    if match:
        return int(match.group(1)) + int(match.group(2))

    match = re.search(r"(?<!\d)(\d{1,3})\s*['’′]", text)
    if match:
        return int(match.group(1))

    # Flashscore sometimes displays a running clock as 80:12.
    match = re.search(r"(?<!\d)(\d{1,3}):\d{2}", text)
    if match:
        return int(match.group(1))

    return None


def get_match_details(driver, match_url, timeout=15):
    """
    Open a Flashscore match and return its current details.

    Return structure:
    {
        "match_id": str,
        "url": str,
        "home_team": str | None,
        "away_team": str | None,
        "home_score": str | None,
        "away_score": str | None,
        "score": str | None,
        "raw_status": str | None,
        "status": "not_started" | "first_half" | "half_time" |
                  "second_half" | "extra_time" | "penalties" |
                  "finished" | "unknown",
        "minute": int | None,
        "is_second_half": bool
    }

    Note: the minute is the displayed elapsed minute. During stoppage time,
    90+3' is returned as 93. The original status is also retained.
    """
    validated = parse_flashscore_match_url(match_url)
    url = validated["url"]

    try:
        driver.get(url)

        WebDriverWait(driver, timeout).until(
            lambda current_driver: (
                _first_text(current_driver, HOME_TEAM_SELECTORS)
                and _first_text(current_driver, AWAY_TEAM_SELECTORS)
            )
        )

    except TimeoutException as error:
        raise MatchPageUnavailableError(
            "The Flashscore match page loaded, but the team details "
            "could not be found."
        ) from error

    except WebDriverException as error:
        raise MatchPageUnavailableError(
            f"Could not open the Flashscore match page: {error}"
        ) from error

    home_team = _first_text(driver, HOME_TEAM_SELECTORS)
    away_team = _first_text(driver, AWAY_TEAM_SELECTORS)

    if not home_team or not away_team:
        raise MatchPageUnavailableError(
            "Flashscore did not expose the home and away team names."
        )

    score_text = _first_text(driver, SCORE_WRAPPER_SELECTORS)
    raw_status = _first_text(driver, STATUS_SELECTORS)

    status = _classify_status(raw_status)
    minute = _parse_minute(raw_status)

    # Extract the two score values from the combined score element.
    # Handles text such as "0\\n-\\n3" or "0 - 3".
    score_match = re.search(
        r"(?<!\d)(\d{1,2})\s*[-–]\s*(\d{1,2})(?!\d)",
        score_text or ""
    )

    home_score = score_match.group(1) if score_match else None
    away_score = score_match.group(2) if score_match else None
    score = (
        f"{home_score} - {away_score}"
        if score_match
        else None
    )

    return {
        "match_id": validated["match_id"],
        "url": url,
        "home_team": home_team,
        "away_team": away_team,
        "home_score": home_score,
        "away_score": away_score,
        "score": score,
        "raw_status": raw_status,
        "status": status,
        "minute": minute,
        "is_second_half": status == "second_half",
    }