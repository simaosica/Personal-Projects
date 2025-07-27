from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time

# Setup Chrome
chrome_options = Options()
# Comment this out to see browser
# chrome_options.add_argument("--headless")
driver = webdriver.Chrome(options=chrome_options)

# Open the commentary page
url = "https://www.flashscore.pt/jogo/futebol/SGFHNgbm/#/sumario-do-jogo/comentarios-ao-vivo/0"
driver.get(url)

try:
    # Let dynamic content load
    time.sleep(5)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # Wait for commentary container to load
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
            text = text_elem.text.strip()

            if minute.startswith("45") and "minuto" in text and "adicionais" in text:
                match = re.search(r"(\d+)\s+minuto", text)
                if match:
                    added_time_1st_half = int(match.group(1))
                    print(f"✅ 1st half added time: {added_time_1st_half} minute(s)")
                    break
        except Exception as e:
            continue

    if added_time_1st_half is None:
        print("⚠️ Could not find 1st half added time.")

except Exception as e:
    print(f"Error: {e}")

driver.quit()
