import re
from selenium.webdriver.common.by import By

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