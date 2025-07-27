from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time

# Lista dos 5 links dos jogos (comentários ao vivo)
match_urls = [
    "https://www.flashscore.pt/jogo/futebol/SGFHNgbm/#/sumario-do-jogo/comentarios-ao-vivo/0",
    "https://www.flashscore.pt/jogo/futebol/rVIQRBBR/#/sumario-do-jogo/comentarios-ao-vivo/0",
    "https://www.flashscore.pt/jogo/futebol/WI9VcoGj/#/sumario-do-jogo/comentarios-ao-vivo/0",
    "https://www.flashscore.pt/jogo/futebol/WdWidu91/#/sumario-do-jogo/comentarios-ao-vivo/0",
    "https://www.flashscore.pt/jogo/futebol/U5XPfbcG/#/sumario-do-jogo/comentarios-ao-vivo/0"
]

# Setup Chrome
chrome_options = Options()
# chrome_options.add_argument("--headless")  # Ativa se quiser rodar sem abrir o browser
driver = webdriver.Chrome(options=chrome_options)

count_3_or_more = 0

for i, url in enumerate(match_urls, start=1):
    print(f"\n🔍 Verificando jogo {i}: {url}")
    driver.get(url)
    
    try:
        time.sleep(5)  # Espera carregar conteúdo dinâmico
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="wcl-commentary"]'))
        )

        all_comments = driver.find_elements(By.CSS_SELECTOR, '[data-testid="wcl-commentary"]')
        added_time_1st_half = None

        for comment in all_comments:
            try:
                minute_elem = comment.find_element(By.CSS_SELECTOR, '[data-testid="wcl-scores-simpleText-02"]')
                text_elem = comment.find_element(By.CSS_SELECTOR, '[data-testid="wcl-commentaryTitle-general"]')
                minute = minute_elem.text.strip()
                text = text_elem.text.strip().lower()

                if minute.startswith("45") and (
                    ("minuto" in text and "adicional" in text) or
                    re.search(r"(\d+)\s*min\.?", text)
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

    except Exception as e:
        print(f"❌ Erro no jogo {i}: {e}")

driver.quit()

# Resultado final
print("\n📊 Resultado:")
print(f"👉 {count_3_or_more} jogo(s) com 3+ minutos de compensação na 1ª parte")

if count_3_or_more <= 1:
    print("✅ Regra cumprida: 0 ou 1 jogo com 3+ minutos")
else:
    print("❌ Regra não cumprida: mais de 1 jogo com 3+ minutos")
