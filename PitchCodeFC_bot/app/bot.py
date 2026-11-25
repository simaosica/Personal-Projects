import asyncio
import os
from urllib.parse import urlsplit

from dotenv import load_dotenv
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
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
        "Welcome to PitchCodeFC Bot!\n"
        "Your football added-time prediction assistant.\n\n"

        "HOW TO USE\n\n"
        "1. Send me a match, for example:\n"
        "   Valencia vs Real Madrid\n\n"

        "2. I'll search Flashscore for the live match.\n"
        "   If multiple matches are found, select the correct one.\n\n"

        "3. Once the match is selected, send /predict.\n"
        "   I'll analyse the second-half commentary and estimate "
        "how much added time the referee will announce.\n\n"

        "You can request a fresh prediction whenever you want.\n\n"

        "COMMANDS\n"
        "/start - Start again\n"
        "/help - Usage instructions\n"
        "/match - Show selected match\n"
        "/predict - Get an added-time prediction\n"
        "/cancel - Clear selected match\n\n"

        "Let's find a match!"
    )



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "PITCHCODEFC BOT — HELP\n\n"

        "FIND A MATCH\n"
        "Send a team matchup, for example:\n"
        "Valencia vs Real Madrid\n\n"
        "You can also send a Flashscore Portugal match URL.\n\n"

        "GET A PREDICTION\n"
        "After selecting a match, send /predict.\n"
        "I'll analyse the second-half commentary and estimate "
        "the total added time the referee will announce.\n\n"

        "You can request another prediction at any time. "
        "Each request uses the latest available match information.\n\n"

        "AVAILABLE COMMANDS\n"
        "/start - Display the welcome message\n"
        "/help - Display these instructions\n"
        "/match - Show your selected match\n"
        "/predict - Generate a fresh prediction\n"
        "/cancel - Clear your selected match\n\n"

        "IMPORTANT\n"
        "Predictions are estimates, not guarantees. "
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

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "Welcome and instructions"),
        BotCommand("help", "Show usage instructions"),
        BotCommand("match", "Show your selected match"),
        BotCommand("predict", "Predict second-half added time"),
        BotCommand("cancel", "Clear your selected match"),
    ])


def main():
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing from your .env file.")

    application: Application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

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