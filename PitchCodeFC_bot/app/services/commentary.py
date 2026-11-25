# getCommentary.py
import re
from urllib.parse import urlsplit, parse_qs

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def get_second_half_commentary(
    driver,
    match_url,
    timeout=15,
    max_minute=None
):
    """
    Extract second-half commentary from a Flashscore match.

    max_minute:
        Optional cutoff minute. Useful for simulating a prediction
        at a particular point in a historical match.
    """

    parsed_url = urlsplit(match_url)
    match_id = parse_qs(parsed_url.query).get("mid", [None])[0]

    if not match_id:
        raise ValueError("Could not find match ID in the URL.")

    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path.rstrip('/')}"

    commentary_url = (
        f"{base_url}/sumario/comentarios-ao-vivo/"
        f"todos-os-comentarios/?mid={match_id}"
    )

    print(f"\nOpening commentary: {commentary_url}")
    driver.get(commentary_url)

    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                '[data-testid="wcl-commentary"]'
            ))
        )
    except TimeoutException:
        print("Commentary did not load.")
        return []

    comments = driver.find_elements(
        By.CSS_SELECTOR,
        '[data-testid="wcl-commentary"]'
    )

    events = []
    seen_events = set()

    for comment in comments:
        try:
            minute_element = comment.find_element(
                By.CSS_SELECTOR,
                '[data-testid="wcl-commentary-headline-text"]'
            )

            description_element = comment.find_element(
                By.CSS_SELECTOR,
                '[data-testid^="wcl-commentaryTitle-"]'
            )

            minute = minute_element.text.strip()
            description = description_element.text.strip()

            if not minute or not description:
                continue

            match = re.match(
                r"^(\d{1,3})(?:\+(\d{1,2}))?",
                minute
            )

            if not match:
                continue

            base_minute = int(match.group(1))
            added_minute = int(match.group(2) or 0)

            # Ignore first-half events.
            if base_minute < 46:
                continue

            # Optional cutoff for historical simulations.
            if max_minute is not None and base_minute > max_minute:
                continue

            event_key = (minute, description)

            if event_key in seen_events:
                continue

            events.append({
                "minute": minute,
                "base_minute": base_minute,
                "added_minute": added_minute,
                "text": description
            })

            seen_events.add(event_key)

        except NoSuchElementException:
            continue

    # Flashscore displays newest events first.
    events.reverse()

    print(f"\nSecond-half events extracted: {len(events)}")

    return events


def format_commentary(events):
    if not events:
        return "No second-half commentary available."

    return "\n".join(
        f"{event['minute']} - {event['text']}"
        for event in events
    )
