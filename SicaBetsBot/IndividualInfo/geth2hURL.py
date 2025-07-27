from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Setup headless Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# Initialize driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

try:
    url = "https://www.flashscore.pt/jogo/futebol/SGFHNgbm/#/h2h/overall"
    driver.get(url)

    wait = WebDriverWait(driver, 15)

    # Aguarda até que todas as secções com jogos apareçam
    all_sections = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.h2h__section.section")))

    if len(all_sections) < 2:
        print("❌ Não foi possível encontrar as secções de últimos jogos.")
    else:
        # Secções dos últimos jogos
        home_section = all_sections[0]
        away_section = all_sections[1]

        # Extrai links dos últimos jogos da equipa da casa
        home_links = home_section.find_elements(By.CSS_SELECTOR, "a.h2h__row")
        home_urls = [a.get_attribute("href").split("#")[0] for a in home_links[:5]]

        # Extrai links dos últimos jogos da equipa visitante
        away_links = away_section.find_elements(By.CSS_SELECTOR, "a.h2h__row")
        away_urls = [a.get_attribute("href").split("#")[0] for a in away_links[:5]]

        # Junta os links
        all_urls = home_urls + away_urls

        print(f"🔗 Total de {len(all_urls)} links (últimos 5 jogos de cada equipa):")
        for i, url in enumerate(all_urls, 1):
            print(f"{i}. {url}")

except Exception as e:
    print("❌ Erro:", e)

finally:
    driver.quit()