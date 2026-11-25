import re
import unicodedata
from urllib.parse import urlsplit, parse_qs

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


FLASHSCORE_LIVE_URL = "https://www.flashscore.pt/futebol/"

# Flashscore changes its CSS classes occasionally. Keep selectors in one
# place so they are easier to update if its page structure changes.
MATCH_ROW_SELECTOR = ".event__match"
HOME_TEAM_SELECTORS = (
    ".event__homeParticipant [data-testid='wcl-simple-text-01']",
    ".event__participant--home",
    '[data-testid="wcl-matchRowParticipantName-home"]',
)
AWAY_TEAM_SELECTORS = (
    ".event__awayParticipant [data-testid='wcl-simple-text-01']",
    ".event__participant--away",
    '[data-testid="wcl-matchRowParticipantName-away"]',
)
HOME_SCORE_SELECTORS = (
    ".event__score--home",
    '[data-testid="wcl-matchRowScore-home"]',
)
AWAY_SCORE_SELECTORS = (
    ".event__score--away",
    '[data-testid="wcl-matchRowScore-away"]',
)
STATUS_SELECTORS = (
    ".event__stage",
    ".event__time",
    ".event__stageTime",
)
MATCH_LINK_SELECTORS = (
    "a.eventRowLink",
    'a[href*="/jogo/futebol/"]',
)


class MatchSearchError(Exception):
    """Base exception for match-search problems."""


class FlashscoreUnavailableError(MatchSearchError):
    """Flashscore could not be loaded or its match list was unavailable."""


class MatchNotFoundError(MatchSearchError):
    """No live match matched the user's search."""


class InvalidMatchInputError(MatchSearchError):
    """The supplied Flashscore URL is not a valid match URL."""


def _normalise(text):
    """Lowercase text and remove accents and punctuation for comparisons."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _first_text(parent, selectors):
    for selector in selectors:
        elements = parent.find_elements(By.CSS_SELECTOR, selector)
        for element in elements:
            value = element.text.strip()
            if value:
                return value
    return ""


def _first_href(parent, selectors):
    for selector in selectors:
        elements = parent.find_elements(By.CSS_SELECTOR, selector)
        for element in elements:
            href = element.get_attribute("href")
            if href and "/jogo/futebol/" in href:
                return href.split("#")[0]
    return ""


def _extract_match(row):
    """Convert one Flashscore event row into a stable dictionary."""
    home = _first_text(row, HOME_TEAM_SELECTORS)
    away = _first_text(row, AWAY_TEAM_SELECTORS)

    # Do not return partially parsed rows: they could produce wrong matches.
    if not home or not away:
        return None

    home_score = _first_text(row, HOME_SCORE_SELECTORS)
    away_score = _first_text(row, AWAY_SCORE_SELECTORS)
    status = _first_text(row, STATUS_SELECTORS)
    url = _first_href(row, MATCH_LINK_SELECTORS)

    if not url:
        return None

    parsed = urlsplit(url)
    match_id = parse_qs(parsed.query).get("mid", [None])[0]

    # Some Flashscore match links identify the match in the path instead
    # of the query string. The path is retained as a fallback identifier.
    if not match_id:
        path_parts = [part for part in parsed.path.split("/") if part]
        if path_parts:
            match_id = path_parts[-1]

    return {
        "home_team": home,
        "away_team": away,
        "score": (
            f"{home_score} - {away_score}"
            if home_score and away_score
            else None
        ),
        "status": status or "Status unavailable",
        "minute": _extract_minute(status),
        "url": url,
        "match_id": match_id,
    }


def _extract_minute(status):
    if not status:
        return None

    match = re.fullmatch(
        r"\s*(\d{1,3})(?:\s*\+\s*(\d{1,2}))?\s*['’′]?\s*",
        status
    )

    if not match:
        return None

    return int(match.group(1)) + int(match.group(2) or 0)


def _is_live_status(status):
    """
    Keep rows that appear to be in progress.

    The minute pattern covers normal and added-time clocks. The text
    patterns cover live states for which Flashscore may not show a minute.
    """
    if not status:
        return False

    if _extract_minute(status) is not None:
        return True

    normalised = _normalise(status)
    live_terms = (
        "intervalo",
        "1 tempo",
        "2 tempo",
        "1a parte",
        "2a parte",
        "prolongamento",
        "penaltis",
        "live",
        "half time",
        "extra time",
    )
    return any(term in normalised for term in live_terms)


def _split_team_query(query):
    """Split common matchup formats into two team names, if supplied."""
    value = query.strip()
    separators = (
        r"\s+vs\.?\s+",
        r"\s+v\s+",
        r"\s+-\s+",
        r"\s+–\s+",
        r"\s+—\s+",
    )

    for separator in separators:
        parts = re.split(separator, value, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2 and all(part.strip() for part in parts):
            return parts[0].strip(), parts[1].strip()

    return None


def _matches_query(match, query):
    teams = (
        _normalise(match["home_team"]),
        _normalise(match["away_team"]),
    )
    pair = _split_team_query(query)

    if pair:
        first, second = (_normalise(part) for part in pair)
        return (
            (first in teams[0] and second in teams[1])
            or (second in teams[0] and first in teams[1])
        )

    needle = _normalise(query)
    return bool(needle) and any(needle in team for team in teams)


def parse_flashscore_match_url(value):
    """
    Validate a Flashscore football match URL.

    Accepts Flashscore URLs containing /jogo/futebol/ and a match id
    in the mid query parameter. Returns a normalised URL and match id.
    """
    value = value.strip()
    parsed = urlsplit(value)

    if (
        parsed.scheme not in ("http", "https")
        or not parsed.netloc.lower().endswith("flashscore.pt")
        or "/jogo/futebol/" not in parsed.path
    ):
        raise InvalidMatchInputError(
            "Please provide a valid Flashscore Portugal football match URL."
        )

    match_id = parse_qs(parsed.query).get("mid", [None])[0]
    if not match_id:
        raise InvalidMatchInputError(
            "The Flashscore URL does not contain a match ID (mid)."
        )

    normalised_url = (
        f"https://www.flashscore.pt{parsed.path.rstrip('/')}/?mid={match_id}"
    )
    return {
        "match_id": match_id,
        "url": normalised_url,
    }


def search_live_matches(driver, query, timeout=15, max_results=10):
    """
    Search all live football matches currently listed by Flashscore.

    `query` may be one team name or a matchup such as
    "Valencia vs Real Madrid".

    Returns a list of dictionaries containing:
        home_team, away_team, score, status, minute, url, match_id

    Raises:
        FlashscoreUnavailableError: Flashscore page/list could not load.
        MatchNotFoundError: no live match matched the query.
    """
    if not query or not query.strip():
        raise ValueError("Please provide at least one team name.")

    try:
        driver.get(FLASHSCORE_LIVE_URL)

        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, MATCH_ROW_SELECTOR)
            )
        )
    except TimeoutException as error:
        raise FlashscoreUnavailableError(
            "Flashscore did not load its football match list in time."
        ) from error
    except WebDriverException as error:
        raise FlashscoreUnavailableError(
            f"Could not open Flashscore: {error}"
        ) from error

    rows = driver.find_elements(By.CSS_SELECTOR, MATCH_ROW_SELECTOR)
    matches = []
    seen_ids = set()

    for row in rows:
        try:
            match = _extract_match(row)
            if not match or not _is_live_status(match["status"]):
                continue

            if not _matches_query(match, query):
                continue

            unique_id = match["match_id"] or match["url"]
            if unique_id in seen_ids:
                continue

            seen_ids.add(unique_id)
            matches.append(match)

            if len(matches) >= max_results:
                break

        except WebDriverException:
            # A row can become stale while Flashscore refreshes its scores.
            continue

    if not matches:
        raise MatchNotFoundError(
            f"No live football match found for '{query}'. "
            "Check the team names or try a Flashscore match URL."
        )

    return matches


def get_match_from_url(value):
    """
    Resolve a user-supplied Flashscore match URL without searching.

    This validates the URL and extracts its match ID. The caller should
    open the returned URL to retrieve the current match status and teams.
    """
    return parse_flashscore_match_url(value)