"""
Application service connecting Flashscore match details, commentary,
and Gemini added-time prediction.

The caller owns the Selenium driver lifecycle. This module does not
create, reuse globally, or close the driver.
"""

from .match_details import (
    get_match_details,
    MatchDetailsError,
)
from .commentary import (
    get_second_half_commentary,
    format_commentary,
)
from .prediction import predict_added_time


class MatchServiceError(Exception):
    """Base exception for match-analysis service errors."""


class MatchNotInSecondHalfError(MatchServiceError):
    """The match is not currently in its second half."""


class InsufficientCommentaryError(MatchServiceError):
    """There is not enough second-half commentary to make a prediction."""


class PredictionServiceError(MatchServiceError):
    """The prediction provider could not return a valid prediction."""


def analyse_match(driver, match_url, timeout=15):
    """
    Retrieve current match details, second-half commentary, and prediction.

    Returns a dictionary with:
      match       Current match details from getMatchDetails.py
      events      Extracted second-half commentary events
      commentary  Human-readable commentary
      prediction  Structured Gemini prediction
    """
    # 1. Retrieve the match's current state.
    try:
        match = get_match_details(driver, match_url, timeout=timeout)
    except MatchDetailsError:
        raise
    except Exception as error:
        raise MatchServiceError(
            f"Could not retrieve match details: {error}"
        ) from error

    # 2. Only make predictions during the second half.
    if match["status"] == "finished":
        raise MatchNotInSecondHalfError(
            f"{match['home_team']} vs {match['away_team']} has finished."
        )

    if match["status"] != "second_half":
        status_messages = {
            "not_started": "The match has not started yet.",
            "first_half": "The match is still in the first half.",
            "half_time": "The match is currently at half-time.",
            "extra_time": (
                "The match is in extra time. "
                "Second-half added-time prediction is not supported."
            ),
            "penalties": "The match is in a penalty shootout.",
            "unknown": "Could not determine the current match period.",
        }
        raise MatchNotInSecondHalfError(
            status_messages.get(
                match["status"],
                "The match is not currently in its second half.",
            )
        )

    current_minute = match.get("minute")
    if current_minute is None or current_minute < 46:
        raise MatchNotInSecondHalfError(
            "Could not confirm a valid second-half match minute."
        )

    # 3. Extract second-half commentary up to the current minute.
    try:
        events = get_second_half_commentary(
            driver,
            match["url"],
            timeout=timeout,
            max_minute=current_minute,
        )
    except Exception as error:
        raise MatchServiceError(
            f"Could not retrieve live commentary: {error}"
        ) from error

    if not events:
        raise InsufficientCommentaryError(
            "No second-half written commentary is available yet. "
            "Please try again later."
        )

    commentary_text = format_commentary(events)

    # 4. Ask Gemini. The predictor accepts match_info as its third,
    # optional argument, so include the known match context.
    match_info = {
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "score": match.get("score"),
        "status": match.get("raw_status"),
        "current_minute": current_minute,
    }

    try:
        prediction = predict_added_time(
            events,
            current_minute,
            match_info=match_info,
        )
    except Exception as error:
        # No fallback model and no fabricated prediction.
        raise PredictionServiceError(
            f"Could not generate the prediction: {error}"
        ) from error

    if not isinstance(prediction, dict):
        raise PredictionServiceError(
            "The prediction module returned an unexpected result."
        )

    return {
        "match": match,
        "events": events,
        "commentary": commentary_text,
        "prediction": prediction,
    }


def format_analysis_result(result):
    """Format the analysis result as a Telegram-friendly text message."""
    match = result["match"]
    prediction = result["prediction"]

    predicted_minutes = prediction.get("predicted_added_time_minutes")
    if (
        not isinstance(predicted_minutes, int)
        or isinstance(predicted_minutes, bool)
    ):
        raise PredictionServiceError(
            "The prediction did not contain a valid "
            "predicted_added_time_minutes value."
        )

    confidence = prediction.get("confidence", "unknown")
    rationale = prediction.get("rationale", "")
    factors = prediction.get("main_factors") or []
    uncertainties = prediction.get("uncertainties", "")

    score = match.get("score")
    matchup = (
        f"{match['home_team']} {score} {match['away_team']}"
        if score
        else f"{match['home_team']} vs {match['away_team']}"
    )

    lines = [
        matchup,
        f"Match minute: {match['minute']}'",
        "",
        f"Predicted second-half added time: +{predicted_minutes} minutes",
        f"Confidence: {confidence}",
    ]

    if rationale:
        lines.extend(["", f"Reasoning: {rationale}"])

    if factors:
        lines.extend(["", "Main factors:"])
        lines.extend(f"- {factor}" for factor in factors)

    if uncertainties:
        lines.extend(["", f"Uncertainties: {uncertainties}"])

    return "\n".join(lines)