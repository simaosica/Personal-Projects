from app.browser import create_headless_chrome_driver
from app.services.match_details import (
    get_match_details,
    MatchDetailsError
)

MATCH_URL = input("Paste a Flashscore match URL: ").strip()


def main():
    driver = create_headless_chrome_driver()

    try:
        details = get_match_details(driver, MATCH_URL)

        print("\n========== MATCH DETAILS ==========")

        for key, value in details.items():
            print(f"{key}: {value}")

        print("===================================")

    except MatchDetailsError as error:
        print(f"Error: {error}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()