from datetime import date
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException





def getTodayGamesAux(driver, league_name, league_url, selected_date):
    import re
    from datetime import datetime

    urls = []

    try:
        driver.delete_all_cookies()
        driver.get(league_url)

        wait = WebDriverWait(driver, 15)

        wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, ".event__match"
            ))
        )

        # Convert selected date to a comparable format
        selected = datetime.strptime(
            selected_date, "%Y-%m-%d"
        ).date()

        match_rows = driver.find_elements(
            By.CSS_SELECTOR, ".event__match"
        )

        print(f"\nChecking {league_name}...")
        print(f"Total results loaded: {len(match_rows)}")

        dates_found = {}

        for row in match_rows:

            try:
                # Extract date/time from the actual match row
                time_element = row.find_element(
                    By.CSS_SELECTOR,
                    ".event__stageTime"
                )

                match_time = time_element.text.strip()

                # Example: 07.11. 20:00
                match_date = re.search(
                    r"(\d{1,2})\.(\d{1,2})\.",
                    match_time
                )

                if not match_date:
                    continue

                day = int(match_date.group(1))
                month = int(match_date.group(2))

                # Use the year supplied by the user
                actual_date = datetime(
                    selected.year, month, day
                ).date()

                date_string = actual_date.isoformat()

                dates_found[date_string] = (
                    dates_found.get(date_string, 0) + 1
                )

                # Only collect matches from the selected date
                if actual_date != selected:
                    continue

                # Extract match URL
                match_link = row.find_element(
                    By.CSS_SELECTOR,
                    "a.eventRowLink"
                )

                href = match_link.get_attribute("href")

                if href:
                    urls.append(href.split("#")[0])

            except Exception as e:
                print(f"Could not process match row: {e}")
                continue

        # Remove duplicate URLs
        urls = list(dict.fromkeys(urls))

        print("\nResults found by date:")

        for match_date, count in dates_found.items():
            print(f"  {match_date}: {count} matches")

        print(
            f"\nMatches selected for {selected_date}: "
            f"{len(urls)}"
        )

        return urls

    except TimeoutException:
        print(f"No results loaded for {league_name}.")
        return []

    except Exception as e:
        print(f"Error processing {league_name}: {e}")
        return []



def getTodayGames(selected_date=None):

    if selected_date is None:
        selected_date = date.today().isoformat()

    date.fromisoformat(selected_date)

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    leagues = {
        "Espanha La Liga":
            "https://www.flashscore.pt/futebol/espanha/laliga/resultados/",
    }

    all_urls = []

    try:
        for league_name, url in leagues.items():
            league_urls = getTodayGamesAux(
                driver,
                league_name,
                url,
                selected_date
            )

            all_urls.extend(league_urls)

    finally:
        driver.quit()

    all_urls = list(dict.fromkeys(all_urls))

    print(
        f"\nNumber of matches to analyse on "
        f"{selected_date}: {len(all_urls)}"
    )

    return all_urls