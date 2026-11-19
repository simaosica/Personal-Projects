
from browser import create_headless_chrome_driver
from getCommentary import (
    get_second_half_commentary,
    format_commentary
)


def main():
    driver = create_headless_chrome_driver()

    try:
        match_url = input("Paste the Flashscore match URL: ").strip()

        # Simulate requesting a prediction at minute 75.
        events = get_second_half_commentary(
            driver,
            match_url,
            max_minute=89
        )

        print("\n========== SECOND HALF TIMELINE ==========\n")
        print(format_commentary(events))
        print("\n==========================================")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()