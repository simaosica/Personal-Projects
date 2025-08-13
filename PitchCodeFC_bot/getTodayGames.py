from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def getTodayGamesAux(driver, league_name, league_url):
    urls = []
    try:
        driver.delete_all_cookies()
        print(f"\n🔍 A aceder à liga: {league_name}")
        driver.get(league_url)

        wait = WebDriverWait(driver, 3)

        # Espera o separador "Jogos de Hoje"
        try:
            jogos_hoje_title = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@class="tabs__ear" and contains(text(), "Jogos de Hoje")]')
                )
            )
        except TimeoutException:
            print(f"❌ Não há jogos hoje na liga {league_name}.")
            return []

        # Acede ao container principal (sobe 3 níveis)
        jogos_hoje_container = jogos_hoje_title.find_element(By.XPATH, '../../..')

        # Espera que pelo menos um link de jogo esteja presente
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, './/div[contains(@id, "g_1_")]//a[contains(@href, "/jogo/futebol/")]')
                )
            )
        except TimeoutException:
            print(f"⚠️ Não foram encontrados jogos visíveis na liga {league_name}.")
            return []

        match_links = jogos_hoje_container.find_elements(By.XPATH, './/div[contains(@id, "g_1_")]//a[contains(@href, "/jogo/futebol/")]')

        for match in match_links:
            href = match.get_attribute("href")
            if href and "/jogo/futebol/" in href:
                urls.append(href.split("#")[0])

        if len(urls) == 0:
            print(f"⚠️ Não há jogos hoje na liga {league_name}. (Nenhum link encontrado)")
        else:
            print(f"✅ Encontrado(s) {len(urls)} jogo(s) de hoje na liga {league_name}")

        return urls

    except Exception as e:
        print(f"❌ Erro ao processar {league_name}: {e}")
        return []

def getTodayGames():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    leagues = {
        "Brasil Série A": "https://www.flashscore.pt/futebol/brasil/serie-a/",
        #"Inglaterra Premier League": "https://www.flashscore.pt/futebol/inglaterra/premier-league/",
        #"Espanha La Liga": "https://www.flashscore.pt/futebol/espanha/laliga/",
        #"Alemanha Bundesliga": "https://www.flashscore.pt/futebol/alemanha/bundesliga/",
        #"Itália Serie A": "https://www.flashscore.pt/futebol/italia/serie-a/",
        #"França Ligue 1": "https://www.flashscore.pt/futebol/franca/ligue-1/",
        #"Portugal Primeira Liga": "https://www.flashscore.pt/futebol/portugal/primeira-liga/",
        "Supertaça UEFA": "https://www.flashscore.pt/futebol/europa/super-taca-da-uefa/",
    }

    all_urls = []
    try:
        for league_name, url in leagues.items():
            league_urls = getTodayGamesAux(driver, league_name, url)
            all_urls.extend(league_urls)
    finally:
        driver.quit()

    print(f"\nTotal de jogos a analisar hoje: {len(all_urls)}")
    return all_urls

# Para testar localmente
#if __name__ == "__main__":
#    jogos_de_hoje = getTodayGames()