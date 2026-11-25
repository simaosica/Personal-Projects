from app.browser import create_headless_chrome_driver
from selenium.webdriver.common.by import By

URL = input("Paste a Flashscore match URL: ").strip()

driver = create_headless_chrome_driver()

try:
    driver.get(URL)

    print("\n========== SCORE ELEMENTS ==========")

    selectors = [
        ".detailScore__wrapper",
        ".detailScore__home",
        ".detailScore__away",
        '[data-testid*="score"]',
        '[class*="score"]',
    ]

    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)

        print(f"\nSelector: {selector}")
        print(f"Elements found: {len(elements)}")

        for element in elements[:10]:
            print(
                f"Text: {element.text!r} | "
                f"Class: {element.get_attribute('class')} | "
                f"Test ID: {element.get_attribute('data-testid')}"
            )

finally:
    driver.quit()