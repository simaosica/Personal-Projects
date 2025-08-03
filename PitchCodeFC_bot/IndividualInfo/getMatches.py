from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get("https://www.flashscore.pt/futebol/brasil/serie-a/")
time.sleep(6)

try:
    accept_btn = driver.find_element(By.ID, "onetrust-accept-btn-handler")
    accept_btn.click()
    time.sleep(2)
except:
    pass

driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(2)

matches = driver.find_elements(By.CSS_SELECTOR, "div.event__match")

print(f"Found {len(matches)} matches")

def get_team_name(participant_div):
    try:
        return participant_div.find_element(By.CSS_SELECTOR, "span[data-testid='wcl-scores-simpleText-01']").text
    except:
        try:
            return participant_div.find_element(By.TAG_NAME, "span").text
        except:
            text = participant_div.text.strip()
            return text if text else "UNKNOWN"

for i, match in enumerate(matches):
    try:
        home_div = match.find_element(By.CSS_SELECTOR, "div.event__homeParticipant")
        away_div = match.find_element(By.CSS_SELECTOR, "div.event__awayParticipant")

        team1 = get_team_name(home_div)
        team2 = get_team_name(away_div)

        if not home_div.is_displayed() or not away_div.is_displayed():
            print(f"[{i}] Skipping invisible match")
            continue

        match_id = match.get_attribute("id").split("_")[-1]
        h2h_url = f"https://www.flashscore.pt/jogo/futebol/{match_id}/#/h2h/ultimos-jogos"

        print(f"[{i}] {team1} vs {team2} -> {h2h_url}")

    except Exception as e:
        print(f"[{i}] Skipping match - missing participants or error: {e}")

driver.quit()
