
from app.browser import create_headless_chrome_driver

from app.services.commentary import (
    get_second_half_commentary,
    format_commentary
)

from app.services.prediction import predict_added_time


MATCH_URL = (
    "https://www.flashscore.pt/jogo/futebol/"
    "real-madrid-W8mj7MDD/valencia-CQeaytrD/"
    "?mid=4SrapZ2c"
)

TEST_MINUTE = 89

MATCH_INFO = {
    "home_team": "Valencia",
    "away_team": "Real Madrid",
    "competition": "La Liga"
}


def main():

    driver = create_headless_chrome_driver()

    try:
        print("\nExtracting match commentary...")

        events = get_second_half_commentary(
            driver,
            MATCH_URL,
            max_minute=TEST_MINUTE
        )

        print(f"\nExtracted {len(events)} events.")

        print("\n========== SECOND HALF TIMELINE ==========\n")
        print(format_commentary(events))
        print("\n==========================================")

    finally:
        driver.quit()

    if not events:
        print("No commentary available. Prediction cancelled.")
        return

    print("\nSending commentary to Gemini...")

    prediction = predict_added_time(
        events=events,
        current_minute=TEST_MINUTE,
        match_info=MATCH_INFO
    )

    print("\n========== AI PREDICTION ==========\n")

    print(
        f"Predicted second-half added time: "
        f"+{prediction['predicted_added_time_minutes']} minutes"
    )

    print(f"Confidence: {prediction['confidence']}")

    print("\nRationale:")
    print(prediction["rationale"])

    print("\nMain factors:")

    for factor in prediction["main_factors"]:
        print(f"- {factor}")

    print("\nUncertainties:")
    print(prediction["uncertainties"])

    print("\n===================================")


if __name__ == "__main__":
    main()