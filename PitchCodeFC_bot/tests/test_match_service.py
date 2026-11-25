from app.browser import create_headless_chrome_driver
from app.services.match_service import (
    analyse_match,
    format_analysis_result,
    MatchServiceError,
)

MATCH_URL = input("Paste a Flashscore match URL: ").strip()


def main():
    driver = create_headless_chrome_driver()

    try:
        result = analyse_match(driver, MATCH_URL)

        print("\n========== ANALYSIS ==========")
        print(format_analysis_result(result))
        print("==============================")

    except MatchServiceError as error:
        print(f"\nAnalysis error: {error}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()