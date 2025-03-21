from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from typing import List
from babel import numbers as bn

# Configure Selenium
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Start WebDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.implicitly_wait(0.1)  # Reduce implicit wait time

print("Install done")

def get_product_name(search_sku) -> str:
    url = f"https://www.long-mcquade.com/instore_stock/{search_sku}/"
    driver.get(url)

    product_link = driver.find_elements(By.CSS_SELECTOR, "a[class*='link-orange-2']")[0]

    product_link.click()

    WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span[id*='product-model']")))

    product_model = driver.find_elements(By.CSS_SELECTOR, "span[id*='product-model']")[0].text.strip()

    return product_model

def scrape_lm_used_listings(search_sku) -> List[dict]:
    url = f"https://www.long-mcquade.com/instore_stock/{search_sku}/"
    driver.get(url)

    # Click all demo buttons at once
    demo_buttons = driver.find_elements(By.CSS_SELECTOR, "p.demo-available")
    for button in demo_buttons:
        try:
            driver.execute_script("arguments[0].scrollIntoView();", button)
            driver.execute_script("arguments[0].click();", button)
        except:
            pass  # Skip if click fails

    print("Pressed all demo buttons")

    # Wait for all tables to load
    WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.demo table.table.demo")))

    print("All tables loaded")

    # Now get all store blocks with the data already loaded
    store_blocks = driver.find_elements(By.CSS_SELECTOR, f"div.row[data-sku='{sku}']")
    used_listings = []

    for store_block in store_blocks:
        # Get store information
        try:
            store_info_div = store_block.find_element(By.CSS_SELECTOR, "div.col-12.col-md-6:nth-child(2)")
            store_name = store_info_div.find_element(By.CSS_SELECTOR, "span.fs-5.fw-bolder").text.strip()

            print(f"FOUND \t | {store_name} ")
        except:
            continue  # Skip if we can't find the store name

        # Check if this store has a demo table
        demo_tables = store_block.find_elements(By.CSS_SELECTOR, "[class*='table demo']")
        if not demo_tables:
            print(f"\t \t | SKIP")
            continue  # Skip if no demo table

        print(f"\t \t | OK")

        # Process the demo table rows
        rows = demo_tables[0].find_elements(By.CSS_SELECTOR, "tbody tr")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 4:
                used_listings.append({
                    "Store": store_name,
                    "SKU": cols[0].text.strip(),
                    "Serial Number": cols[1].text.strip(),
                    "Condition": cols[2].text.strip(),
                    "Price": float(bn.parse_decimal(cols[3].text.strip().replace("$", ""), locale="en_US"))
                })

    return used_listings


skus = [
    "524892",
    "385148",
    "726449",
    "742640",
    "808888",
    "385147",
    "726448"
]

writer = pd.ExcelWriter("Stock.xlsx", engine="xlsxwriter")

for sku in skus:
    print("\n-----------------------------------\n")
    product_name = get_product_name(sku)
    print(f"{product_name} - {sku}\n")
    sheet_name = f"{product_name} ({sku})"
    listings = scrape_lm_used_listings(sku)
    stock_df = pd.DataFrame(listings)
    stock_df.sort_values(by="Price", axis=0, ascending=True, inplace=True)
    stock_df.to_excel(writer, sheet_name=sheet_name, index=False)

    currency_format = writer.book.add_format({"num_format": "$#,##0.00;-$#,##0.00"})
    writer.sheets[sheet_name].autofit()

    price_width = max(stock_df["Price"].astype(str).map(len).max(), len("Price"))
    writer.sheets[sheet_name].set_column(4, 4, width=round(1.5*price_width), cell_format=currency_format)

writer.close()

# Close WebDriver
driver.quit()