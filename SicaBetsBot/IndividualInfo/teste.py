from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
import time

# Setup headless Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# Inicializa driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

try:
    # URL do jogo inicial para obter os 5 confrontos diretos (H2H)
    base_url = "https://www.flashscore.pt/jogo/futebol/tKuixgDt/#/h2h/overall"
    print(f"🔎 A buscar confrontos diretos para o jogo: {base_url}")
    driver.get(base_url)

    wait = WebDriverWait(driver, 15)

    # Espera pelas secções com jogos aparecerem
    all_sections = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.rows")))

    if len(all_sections) < 3:
        print("❌ Não foi possível encontrar a secção de confrontos diretos (H2H).")
        match_urls = []
    else:
        h2h_section = all_sections[2]  # 3ª secção = Confrontos Diretos

        # Extrai os links dos jogos dentro da secção de H2H
        match_links = h2h_section.find_elements(By.CSS_SELECTOR, "a.h2h__row")

        if not match_links:
            print("❌ Nenhum confronto direto encontrado.")
            match_urls = []
        else:
            print("✅ 5 confrontos diretos encontrados:")
            match_urls = []
            for i, a in enumerate(match_links[:5], 1):  # só os 5 mais recentes
                href = a.get_attribute("href")
                print(f"{i}. {href}")
                # Ajusta URL para os comentários ao vivo:
                href_comments = href.replace("#/sumario-do-jogo", "#/sumario-do-jogo/comentarios-ao-vivo/0")
                match_urls.append(href_comments)

    count_3_or_more = 0

    # Agora verifica os tempos adicionados na 1ª parte para cada um dos 5 jogos
    for i, url in enumerate(match_urls, start=1):
        print(f"\n🔍 Verificando jogo {i}: {url}")
        driver.get(url)
        
        try:
            time.sleep(5)  # Espera conteúdo dinâmico carregar
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="wcl-commentary"]'))
            )

            all_comments = driver.find_elements(By.CSS_SELECTOR, '[data-testid="wcl-commentary"]')

            if not all_comments:
                print("⚠️ Não há dados disponíveis sobre este jogo.")
                continue

            added_time_1st_half = None

            for comment in all_comments:
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
                            added_time_1st_half = int(match.group(1))
                            print(f"🕒 Adicionado {added_time_1st_half} minuto(s) à 1ª parte")
                            if added_time_1st_half >= 3:
                                count_3_or_more += 1
                            break
                except Exception:
                    continue

            if added_time_1st_half is None:
                print("⚠️ Não foi possível encontrar o tempo de compensação da 1ª parte.")

        except (TimeoutException, NoSuchElementException):
            print("⚠️ Não há comentários disponíveis para este jogo.")
        except Exception as e:
            print(f"❌ Erro no jogo {i}: {e}")

finally:
    driver.quit()

# Resultado final
print("\n📊 Resultado:")
print(f"👉 {count_3_or_more} jogo(s) com 3+ minutos de compensação na 1ª parte")

if count_3_or_more <= 1:
    print("✅ Regra cumprida: 0 ou 1 jogo com 3+ minutos")
else:
    print("❌ Regra não cumprida: mais de 1 jogo com 3+ minutos")