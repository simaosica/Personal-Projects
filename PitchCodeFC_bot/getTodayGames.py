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
        print(f"\n🔍 Checking league: {league_name}")
        driver.get(league_url)

        wait = WebDriverWait(driver, 3)

        # Wait for the "Today's Matches" tab
        try:
            jogos_hoje_title = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@class="tabs__ear" and contains(text(), "Jogos de Hoje")]')
                )
            )
        except TimeoutException:
            print(f"❌ No matches today in {league_name}.")
            return []

        # Access the main container (go up 3 levels)
        jogos_hoje_container = jogos_hoje_title.find_element(By.XPATH, '../../..')

        # Wait for at least one match link to be present
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, './/div[contains(@id, "g_1_")]//a[contains(@href, "/jogo/futebol/")]')
                )
            )
        except TimeoutException:
            print(f"⚠️ NNo visible matches found in {league_name}.")
            return []

        match_links = jogos_hoje_container.find_elements(By.XPATH, './/div[contains(@id, "g_1_")]//a[contains(@href, "/jogo/futebol/")]')

        for match in match_links:
            href = match.get_attribute("href")
            if href and "/jogo/futebol/" in href:
                urls.append(href.split("#")[0])

        if len(urls) == 0:
            print(f"⚠️ No matches today in {league_name}. (No links found)")
        else:
            print(f"✅ Found {len(urls)} match(es) today in {league_name}")

        return urls

    except Exception as e:
        print(f"❌ Error processing {league_name}: {e}")
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
        "Brazil Serie A": "https://www.flashscore.pt/futebol/brasil/serie-a/",
        "England Premier League": "https://www.flashscore.pt/futebol/inglaterra/premier-league/",
        "Spain La Liga": "https://www.flashscore.pt/futebol/espanha/laliga/",
        "Germany Bundesliga": "https://www.flashscore.pt/futebol/alemanha/bundesliga/",
        "Italy Serie A": "https://www.flashscore.pt/futebol/italia/serie-a/",
        "France Ligue 1": "https://www.flashscore.pt/futebol/franca/ligue-1/",
        "Portugal Primeira Liga": "https://www.flashscore.pt/futebol/portugal/primeira-liga/",
        #"UEFA Super Cup": "https://www.flashscore.pt/futebol/europa/super-taca-da-uefa/",
    }

    all_urls = []
    try:
        for league_name, url in leagues.items():
            league_urls = getTodayGamesAux(driver, league_name, url)
            all_urls.extend(league_urls)
    finally:
        driver.quit()

    print(f"\nNumber of matches to analyse today: {len(all_urls)}")
    return all_urls

# Para testar localmente
#if __name__ == "__main__":
#    jogos_de_hoje = getTodayGames()