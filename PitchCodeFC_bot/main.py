import asyncio
import time
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
    output += f"\n   🔍 Verificando jogo {index}: {home_i} - {away_i}\n"

    comments_container = wait_for_element(driver, '[data-testid="wcl-commentary"]', timeout=8)
    if not comments_container:
        return output + "   ⚠️ Não foi possível encontrar o tempo de compensação da 1ª parte.\n", None

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
        output += f"   🕒 O tempo adicionado à 1ª parte desse jogo foi de {added_time} minuto(s).\n"
    else:
        output += "   ⚠️ Não foi possível encontrar o tempo de compensação da 1ª parte. Não há dados disponíveis.\n"

    return output, added_time


def process_game(driver, base_url, game_index, total_games):
    output = ""
    driver.get(base_url)
    home, away = extract_teams(driver)

    output += f"\n🎯 [{game_index}/{total_games}] A avaliar o jogo: {home} - {away}\n"

    h2h_url = base_url + "#/h2h/overall"
    driver.get(h2h_url)

    all_sections = wait_for_element(driver, "div.rows", timeout=10, by=By.CSS_SELECTOR)
    if not all_sections:
        output += "❌ Timeout ao carregar secções H2H.\n"
        return output

    all_sections = driver.find_elements(By.CSS_SELECTOR, "div.rows")
    if len(all_sections) < 3:
        output += "❌ Não foi possível encontrar a secção de H2H.\n"
        return output

    home_section = all_sections[0]
    away_section = all_sections[1]

    home_urls = get_match_urls_from_section(home_section, limit=5)
    away_urls = get_match_urls_from_section(away_section, limit=5)

    match_urls = home_urls + away_urls
    if not match_urls:
        output += "❌ Nenhum confronto direto encontrado.\n"
        return output

    count_3_or_more = 0
    for i, url in enumerate(match_urls[:2], start=1):  # Adjust how many matches to check here
        match_output, added_time = process_match(driver, url, i)
        output += match_output
        if added_time is not None and added_time >= 3:
            count_3_or_more += 1

    output += "\n📊 Resultado:\n"
    if count_3_or_more <= 3:
        output += f"✅ Vamos estar muito atentos ao jogo {home} - {away}: Apenas {count_3_or_more}/10 jogos anteriores destas duas equipas tiveram 4 ou mais minutos de compensação na 1ª parte.\n"
    else:
        output += f"❌ Ficamos de fora no jogo {home} - {away}: {count_3_or_more}/10 jogos anteriores destas duas equipas tiveram 4 ou mais minutos de compensação na 1ª parte.\n"

    return output


def main():
    driver = create_headless_chrome_driver()

    try:
        game_urls = getTodayGames()
        total_games = len(game_urls)

        for game_index, base_url in enumerate(game_urls, 1):
            output = process_game(driver, base_url, game_index, total_games)
            print(output)
            # asyncio.run(send_telegram_message(output))  # Uncomment to send telegram messages

    except Exception as e:
        final_error_msg = f"❌ Erro geral: {e}\n"
        print(final_error_msg)
        # asyncio.run(send_telegram_message(final_error_msg)) # Uncomment to send telegram messages

    finally:
        if total_games > 0:
            print("\n ⚠️ Se houve algum penalti, substituição, intervenção do VAR ou cartão vermelho ficamos de fora.")
        driver.quit()


if __name__ == "__main__":
    main()