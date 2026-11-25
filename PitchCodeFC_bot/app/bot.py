import asyncio
import os
from urllib.parse import urlsplit

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .browser import create_headless_chrome_driver
from .services.match_search import (
    search_live_matches,
    get_match_from_url,
    MatchSearchError,
)
from .services.match_details import get_match_details, MatchDetailsError
from .services.match_service import analyse_match, format_analysis_result, MatchServiceError


load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def _search_matches(query):
    """Run a Flashscore search in a worker thread with its own driver."""
    driver = create_headless_chrome_driver()
    try:
        return search_live_matches(driver, query)
    finally:
        driver.quit()


def _validate_match_url(url):
    """Validate a supplied URL and retrieve the current match details."""
    driver = create_headless_chrome_driver()
    try:
        validated = get_match_from_url(url)
        return get_match_details(driver, validated["url"])
    finally:
        driver.quit()


def _run_prediction(match_url):
    """Run one fresh, user-requested prediction with a new browser session."""
    driver = create_headless_chrome_driver()
    try:
        result = analyse_match(driver, match_url)
        return format_analysis_result(result)
    finally:
        driver.quit()


def _match_label(match):
    score = match.get("score")
    status = match.get("status") or match.get("raw_status") or "Status unavailable"
    label = f"{match['home_team']} vs {match['away_team']}"
    if score:
        label += f" ({score})"
    return f"{label} — {status}"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("active_match", None)
    context.user_data.pop("pending_matches", None)
    await update.effective_message.reply_text(
        "Welcome to PitchCodeFC Bot!\n\n"
        "Send a team matchup (e.g. Valencia vs Real Madrid) or a "
        "Flashscore Portugal match URL.\n\n"
        "After selecting a match, send /predict whenever you want a "
        "fresh second-half added-time prediction.\n\n"
        "Commands:\n"
        "/predict — get or refresh the prediction\n"
        "/match — show your selected match\n"
        "/cancel — clear your selected match\n"
        "/help — show these instructions"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Send a team matchup (e.g. Valencia vs Real Madrid) or a "
        "Flashscore Portugal match URL.\n\n"
        "/predict — get or refresh the prediction\n"
        "/match — show your selected match\n"
        "/cancel — clear your selected match\n"
        "/help — show these instructions"
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("active_match", None)
    context.user_data.pop("pending_matches", None)
    await update.effective_message.reply_text(
        "Your selected match has been cleared. Send another matchup or "
        "Flashscore URL to choose a match."
    )


async def match_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match = context.user_data.get("active_match")
    if not match:
        await update.effective_message.reply_text(
            "You haven't selected a match yet. Send a team matchup or "
            "Flashscore URL first."
        )
        return

    await update.effective_message.reply_text(
        f"Selected match:\n{_match_label(match)}\n\n"
        "Send /predict to get a fresh prediction."
    )


async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match = context.user_data.get("active_match")
    if not match:
        await update.effective_message.reply_text(
            "Select a match first by sending a team matchup or a Flashscore URL."
        )
        return

    status_message = await update.effective_message.reply_text(
        f"Checking {match['home_team']} vs {match['away_team']} and "
        "retrieving the latest commentary..."
    )

    try:
        prediction_text = await asyncio.to_thread(_run_prediction, match["url"])
        await status_message.edit_text(prediction_text)
    except MatchServiceError as error:
        await status_message.edit_text(f"Unable to generate a prediction:\n{error}")
    except Exception:
        await status_message.edit_text(
            "A temporary error occurred while analysing the match. "
            "Please try again shortly."
        )
        raise


async def handle_match_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    pending = context.user_data.get("pending_matches", [])
    try:
        index = int(query.data.split(":", 1)[1])
        selected = pending[index]
    except (ValueError, IndexError):
        await query.edit_message_text(
            "That match selection has expired. Please send the matchup again."
        )
        return

    context.user_data["active_match"] = selected
    context.user_data.pop("pending_matches", None)
    await query.edit_message_text(
        f"Match selected:\n{_match_label(selected)}\n\n"
        "Send /predict whenever you want a fresh prediction."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.effective_message.text or "").strip()
    if not text:
        return

    status_message = await update.effective_message.reply_text(
        "Looking up the match on Flashscore..."
    )

    try:
        parsed = urlsplit(text)

        if parsed.scheme in ("http", "https") and parsed.netloc:
            match = await asyncio.to_thread(_validate_match_url, text)
            context.user_data["active_match"] = match
            context.user_data.pop("pending_matches", None)
            await status_message.edit_text(
                f"Match found:\n{_match_label(match)}\n\n"
                "Send /predict to request a prediction. You can send /predict "
                "again later for an updated estimate."
            )
            return

        matches = await asyncio.to_thread(_search_matches, text)

        if len(matches) == 1:
            selected = matches[0]
            context.user_data["active_match"] = selected
            context.user_data.pop("pending_matches", None)
            await status_message.edit_text(
                f"Match found:\n{_match_label(selected)}\n\n"
                "Send /predict to request a prediction. You can send /predict "
                "again later for an updated estimate."
            )
            return

        context.user_data["pending_matches"] = matches
        buttons = [
            [
                InlineKeyboardButton(
                    _match_label(match)[:64],
                    callback_data=f"select:{index}",
                )
            ]
            for index, match in enumerate(matches)
        ]
        await status_message.edit_text(
            "I found multiple live matches matching your search. "
            "Please select the correct one:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except MatchSearchError as error:
        await status_message.edit_text(str(error))
    except MatchDetailsError as error:
        await status_message.edit_text(f"Could not retrieve match details:\n{error}")
    except Exception:
        await status_message.edit_text(
            "A temporary error occurred while contacting Flashscore. "
            "Please try again shortly."
        )
        raise


def main():
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing from your .env file.")

    application: Application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("predict", predict_command))
    application.add_handler(CommandHandler("match", match_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(
        CallbackQueryHandler(handle_match_selection, pattern=r"^select:\d+$")
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    print("PitchCodeFC Bot is running. Press Ctrl+C to stop.")
    application.run_polling()


if __name__ == "__main__":
    main()