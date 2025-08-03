from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set up the browser
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 15)

# Match URL (finished match)
url = "https://www.flashscore.pt/jogo/futebol/SGFHNgbm/"
driver.get(url)

try:
    print("Page title:", driver.title)

    # Wait for the score wrapper to load
    score_wrapper = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".detailScore__wrapper")))
    spans = score_wrapper.find_elements(By.TAG_NAME, "span")

    if len(spans) >= 3:
        home_score = spans[0].text
        away_score = spans[2].text
        print(f"✅ Final Score: {home_score} - {away_score}")
    else:
        print("⚠️ Score format unexpected")

except Exception as e:
    print(f"❌ Failed to get score: {e}")

driver.quit()
