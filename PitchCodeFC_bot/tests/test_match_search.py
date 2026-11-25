
from app.browser import create_headless_chrome_driver
from app.services.match_search import search_live_matches, MatchSearchError

driver = create_headless_chrome_driver()

try:
    query = input("Enter matchup: ").strip()

    matches = search_live_matches(driver, query)

    print(f"\nMatches found: {len(matches)}")

    for match in matches:
        for key, value in match.items():
            print(f"{key}: {value}")
        print("--------------------")

except MatchSearchError as error:
    print(f"Search error: {error}")

finally:
    driver.quit()
