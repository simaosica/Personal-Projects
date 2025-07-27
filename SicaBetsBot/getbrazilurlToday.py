from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Função para obter URLs dos jogos de hoje na Série A do Brasil
def get_today_game_urls():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    try:
        print("🔍 A aceder à página da Série A do Brasil...")
        driver.get("https://www.flashscore.pt/futebol/brasil/serie-a/")

        wait = WebDriverWait(driver, 10)  # Espera até 10 segundos
        jogos_hoje_title = wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[@class="tabs__ear" and contains(text(), "Jogos de Hoje")]'))
        )
        jogos_hoje_container = jogos_hoje_title.find_element(By.XPATH, '../../..')  # Sobe 3 níveis

        match_links = jogos_hoje_container.find_elements(By.XPATH, './/div[contains(@id, "g_1_")]//a[contains(@href, "/jogo/futebol/")]')

        urls = []
        for match in match_links:
            href = match.get_attribute("href")
            if href and "/jogo/futebol/" in href:
                urls.append(href.split("#")[0])  # Remove fragmentos após '#'

        print(f"✅ Encontrados {len(urls)} jogos de hoje na Série A do Brasil:")
        #for url in urls:
        #    print(url)

        return urls

    except Exception as e:
        print(f"❌ Erro: {e}")
        return []

    finally:
        driver.quit()

#if __name__ == "__main__":
#    get_today_game_urls()