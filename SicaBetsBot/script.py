import asyncio
import re
import time
from telegram import Bot
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from getTodayGames import getTodayGames

# Config Telegram
BOT_TOKEN = '8154995039:AAFhWvCaWus5VkA5QJFUZ6ar20vsuNUy9tc'  # token
CHAT_ID = -1002786394948  # chat ID

async def send_telegram_message(text):
    bot = Bot(token=BOT_TOKEN)
    # Telegram tem limite de tamanho por mensagem (4096 chars)
    chunk_size = 4000
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size]
        await bot.send_message(chat_id=CHAT_ID, text=chunk)

# Setup headless Chrome com otimizações
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-images")
chrome_options.add_argument("--disable-javascript")
chrome_options.add_argument("--disable-plugins")
chrome_options.add_argument("--disable-extensions")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def wait_for_element(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
    except TimeoutException:
        return None

def extract_added_time(comments):
    for comment in comments:
        try:
            minute_elem = comment.find_element(By.CSS_SELECTOR, '[data-testid="wcl-scores-simpleText-02"]')
            text_elem = comment.find_element(By.CSS_SELECTOR, '[data-testid="wcl-commentaryTitle-general"]')
            minute = minute_elem.text.strip()
            text = text_elem.text.strip().lower()

            if minute.startswith("45") and (
                ("minuto" in text and "adicional" in text) or
                re.search(r"(\d+)\s*min\.?", text) or
                "min." in text and ("adicionado" in text or "adicionais" in text or "compensação" in text)
            ):
                match = re.search(r"(\d+)\s*(?:minuto|min)\.?", text)
                if match:
                    return int(match.group(1))
        except Exception:
            continue
    return None

try:
    game_urls = getTodayGames()

    for game_index, base_url in enumerate(game_urls, 1):
        output = ""  # reset output para este jogo

        # Extrair nomes das equipas do jogo principal
        home = ""
        away = ""

        driver.get(base_url)
        try:
            team_elements = WebDriverWait(driver, 8).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.participant__participantName"))
            )
            if len(team_elements) >= 2:
                home = team_elements[0].text.strip()
                away = team_elements[1].text.strip()
            else:
                home = "Casa"
                away = "Fora"
        except Exception:
            home = "Casa"
            away = "Fora"

        output += f"\n🎯 [{game_index}/{len(game_urls)}] A avaliar o jogo: {home} - {away}\n"

        h2h_url = base_url + "#/h2h/overall"
        driver.get(h2h_url)

        all_sections = wait_for_element(driver, "div.rows", timeout=10, by=By.CSS_SELECTOR)
        if not all_sections:
            output += "❌ Timeout ao carregar secções H2H.\n"
            print(output)
            asyncio.run(send_telegram_message(output))
            continue

        all_sections = driver.find_elements(By.CSS_SELECTOR, "div.rows")
        if len(all_sections) < 3:
            output += "❌ Não foi possível encontrar a secção de H2H.\n"
            print(output)
            asyncio.run(send_telegram_message(output))
            continue

        home_section = all_sections[0]
        away_section = all_sections[1]

        home_links = home_section.find_elements(By.CSS_SELECTOR, "a.h2h__row")
        home_urls = [a.get_attribute("href").split("#")[0] for a in home_links[:5]]

        away_links = away_section.find_elements(By.CSS_SELECTOR, "a.h2h__row")
        away_urls = [a.get_attribute("href").split("#")[0] for a in away_links[:5]]

        match_links = home_links + away_links

        if not match_links:
            output += "❌ Nenhum confronto direto encontrado.\n"
            print(output)
            asyncio.run(send_telegram_message(output))
            continue

        match_urls = []
        for a in match_links[:10]:
            href = a.get_attribute("href")
            href_comments = href.replace("#/sumario-do-jogo", "#/sumario-do-jogo/comentarios-ao-vivo/0")
            match_urls.append(href_comments)

        count_4_or_more = 0

        for i, url in enumerate(match_urls, start=1):
            # Extrair nomes das equipas do jogo verificado
            driver.get(url)
            home_i = ""
            away_i = ""
            try:
                team_i_elements = WebDriverWait(driver, 8).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.participant__participantName"))
                )
                if len(team_i_elements) >= 2:
                    home_i = team_i_elements[0].text.strip()
                    away_i = team_i_elements[1].text.strip()
                else:
                    home_i = "Casa"
                    away_i = "Fora"
            except Exception:
                home_i = "Casa"
                away_i = "Fora"

            output += f"\n   🔍 Verificando jogo {i}: {home_i} - {away_i}\n"

            try:
                comments_container = wait_for_element(
                    driver,
                    '[data-testid="wcl-commentary"]',
                    timeout=8
                )

                if not comments_container:
                    output += "   ⚠️ Não foi possível encontrar o tempo de compensação da 1ª parte.\n"
                    continue

                driver.execute_script("""
                    const container = document.querySelector('[data-testid="wcl-commentary"]').parentElement;
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                    }
                """)

                time.sleep(1)

                all_comments = driver.find_elements(By.CSS_SELECTOR, '[data-testid="wcl-commentary"]')
                added_time_1st_half = extract_added_time(all_comments)

                if added_time_1st_half is not None:
                    output += f"   🕒 O tempo adicionado à 1ª parte desse jogo foi de {added_time_1st_half} minuto(s).\n"
                    if added_time_1st_half >= 4:
                        count_4_or_more += 1
                else:
                    output += "   ⚠️ Não foi possível encontrar o tempo de compensação da 1ª parte. Não há dados disponíveis.\n"

            except Exception as e:
                output += f"   ❌ Erro ao processar jogo {i}: {e}\n"

        output += "\n📊 Resultado:\n"

        if count_4_or_more <= 3:
            output += f"✅ Vamos estar muito atentos ao jogo {home} - {away}: Apenas {count_4_or_more}/10 jogos anteriores destas duas equipas tiveram 4 ou mais minutos de compensação na 1ª parte.\n"
        else:
            output += f"❌ Ficamos de fora no jogo {home} - {away}: {count_4_or_more}/10 jogos anteriores destas duas equipas tiveram 4 ou mais minutos de compensação na 1ª parte.\n"

        print(output)  # Imprime no terminal
        #asyncio.run(send_telegram_message(output))  # Envia a mensagem para o Telegram

except Exception as e:
    final_error_msg = f"❌ Erro geral: {e}\n"
    print(final_error_msg)
    asyncio.run(send_telegram_message(final_error_msg))

finally:
    print("\n\n ⚠️ Se houve algum penalti, substituição, intervenção do VAR ou cartão vermelho, o tempo de compensação pode ser diferente. Nesses casos temos de ter cuidado.")
    driver.quit()