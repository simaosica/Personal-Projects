import asyncio
import time
import math
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from getTodayGames import getTodayGames
from extractTime import extract_added_time
from telegramBot import send_telegram_message
from browser import create_headless_chrome_driver


def wait_for_element(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
    except TimeoutException:
        return None


def extract_teams(driver):
    try:
        team_elements = WebDriverWait(driver, 8).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.participant__participantName"))
        )
        if len(team_elements) >= 2:
            return team_elements[0].text.strip(), team_elements[1].text.strip()
    except Exception:
        pass
    return "Casa", "Fora"


def get_match_urls_from_section(section, limit=5):
    links = section.find_elements(By.CSS_SELECTOR, "a.h2h__row")
    urls = []
    for a in links[:limit]:
        href = a.get_attribute("href")
        href_comments = href.replace("#/sumario-do-jogo", "#/sumario-do-jogo/comentarios-ao-vivo/0")
        urls.append(href_comments)
    return urls


def process_match(driver, url, index):
    output = ""
    driver.get(url)
    home_i, away_i = extract_teams(driver)
    output += f"\n   🔍 Analysing: {index}: {home_i} - {away_i}\n"

    comments_container = wait_for_element(driver, '[data-testid="wcl-commentary"]', timeout=8)
    if not comments_container:
        return output + "   ⚠️ Cannot find 1st Half added time.\n", None

    driver.execute_script("""
        const container = document.querySelector('[data-testid="wcl-commentary"]').parentElement;
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    """)
    time.sleep(1)

    all_comments = driver.find_elements(By.CSS_SELECTOR, '[data-testid="wcl-commentary"]')
    added_time = extract_added_time(all_comments)

    if added_time is not None:
        output += f"   🕒 1st Half added time: {added_time} minute(s).\n"
    else:
        output += "   ⚠️ Cannot find 1st Half added time. No data available.\n"

    return output, added_time


def process_game(driver, base_url, game_index, total_games):
    output = ""
    driver.get(base_url)
    home, away = extract_teams(driver)

    output += f"\n🎯 [{game_index}/{total_games}] Analysing: {home} - {away}\n"

    h2h_url = base_url + "#/h2h/overall"
    driver.get(h2h_url)

    all_sections = wait_for_element(driver, "div.rows", timeout=10, by=By.CSS_SELECTOR)
    if not all_sections:
        output += "❌ Timeout while loading H2H sections.\n"
        return output

    all_sections = driver.find_elements(By.CSS_SELECTOR, "div.rows")
    if len(all_sections) < 3:
        output += "❌ Could not find H2H section.\n"
        return output

    home_section = all_sections[0]
    away_section = all_sections[1]

    home_urls = get_match_urls_from_section(home_section, limit=5)
    away_urls = get_match_urls_from_section(away_section, limit=5)

    match_urls = home_urls + away_urls
    if not match_urls:
        output += "❌ No H2H match found.\n"
        return output

    added_times = []
    for i, url in enumerate(match_urls[:10], start=1):  # Adjust how many matches to check here
        match_output, added_time = process_match(driver, url, i)
        output += match_output
        if added_time is not None:
            added_times.append(added_time) # Store added time for analysis

    output += f"\n📊 Analysing: {home} - {away}:\n"

    if added_times:
        # Calculate average expected time and round it up
        avg_expected_time = math.ceil(sum(added_times) / len(added_times))

        # Check if we have enough data points and if the average is low
        if avg_expected_time < 4 and len(added_times) >= 5:
            output += f"⏳ Expected 1st Half added time: {avg_expected_time} minute(s).\n"
            output += f"✅ We'll be keeping a close eye on the match {home} - {away}.\n"
        else:
            output += f"❌ We're not sure about the match {home} - {away}.\n"
    else:
        output += "❔ Not enough data to calculate expected added time.\n"

    return output


def main():
    driver = create_headless_chrome_driver()

    try:
        game_urls = getTodayGames()
        total_games = len(game_urls)

        for game_index, base_url in enumerate(game_urls, 1):
            output = process_game(driver, base_url, game_index, total_games)
            print(output)
            #asyncio.run(send_telegram_message(output))  # Uncomment to send telegram messages

    except Exception as e:
        final_error_msg = f"❌ Error: {e}\n"
        print(final_error_msg)
        #asyncio.run(send_telegram_message(final_error_msg)) # Uncomment to send telegram messages

    finally:
        if total_games > 0:
            print("\n ⚠️ If there were any penalties, substitutions, VAR interventions, or red cards, we should ignore them.")
        driver.quit()


if __name__ == "__main__":
    main()