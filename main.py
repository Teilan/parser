import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
from selenium.common.exceptions import TimeoutException

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-images')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def extract_product_info(product_card, main_url, brand_pattern):
    product_info = {}
    
    product_id = product_card.get('id')
    product_info['ID'] = product_id if product_id else 'ID не найден'

    product_links = product_card.find_all('a')
    seen_urls = set()
    for link in product_links:
        title = link.get('title')
        href = link.get('href')
        link_text = link.get_text(strip=True)
        
        if href and href not in seen_urls:
            seen_urls.add(href)
            product_info['Ссылка'] = main_url + href
        
        if link_text:
            product_info['Название'] = link_text
    
    promo_price_elements = product_card.find_all('span', class_='product-price nowrap product-unit-prices__actual style--catalog-2-level-product-card-major-actual color--red')
    regular_price_elements = product_card.find_all('span', class_='product-price nowrap product-unit-prices__old style--catalog-2-level-product-card-major-old')
    fallback_regular_price_elements = product_card.find_all('span', class_='product-price nowrap product-unit-prices__actual style--catalog-2-level-product-card-major-actual')
    
    if promo_price_elements:
        product_info['Промо цена'] = promo_price_elements[0].text.strip()
    
    if regular_price_elements:
        product_info['Регулярная цена'] = regular_price_elements[0].text.strip()
    elif fallback_regular_price_elements:
        product_info['Регулярная цена'] = fallback_regular_price_elements[0].text.strip()

    product_name = product_info.get('Название', '').lower()
    if "metro chef" in product_name:
        product_info['Бренд'] = "METRO Chef"
    else:
        brand_match = re.search(brand_pattern, product_name)
        if brand_match:
            product_info['Бренд'] = brand_match.group(0).capitalize()
        else:
            product_info['Бренд'] = 'Бренд не найден'
    
    return product_info

def extract_products_from_page(driver, page_url, main_url, brand_pattern):
    driver.get(page_url)
    
    try:
        WebDriverWait(driver, 120).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'catalog-2-level-product-card'))
        )
    except TimeoutException:
        # print("Тайм-аут загрузки страницы, перезапускаем драйвер.")
        driver.quit()
        driver = init_driver()

    page_html = driver.page_source
    soup = BeautifulSoup(page_html, 'html.parser')

    product_cards = soup.find_all('div', class_='catalog-2-level-product-card')
    if not product_cards:
        # print("Продукты на странице не найдены.")
        return []

    products_data = []
    for product_card in product_cards:
        product_info = extract_product_info(product_card, main_url, brand_pattern)
        products_data.append(product_info)

    return products_data

def scrape_products(category_url, main_url, brand_pattern, max_pages=1):
    driver = init_driver()
    products_data = []
    for page_number in range(1, max_pages + 1):
        current_url = f"{category_url}&page={page_number}" if page_number > 1 else category_url
        # print(f"Загружаем страницу: {current_url}")
        
        page_data = extract_products_from_page(driver, current_url, main_url, brand_pattern)
        if not page_data:
            # print("Продукты на странице не найдены, возможно, достигнут конец.")
            break
        
        products_data.extend(page_data)

    driver.quit()
    return products_data

def main():
    main_url = 'https://online.metro-cc.ru'
    category_url = "https://online.metro-cc.ru/category/molochnye-prodkuty-syry-i-yayca/syry/polutverdye?from=under_search"
    brand_pattern = r'(?<=сыр\s)(\w+|\w+\s\w+)'

    products_data = scrape_products(category_url, main_url, brand_pattern, max_pages=8)

    if products_data:
        df = pd.DataFrame(products_data)
        df.to_excel('products_with_prices_and_brands.xlsx', index=False, engine='openpyxl')
        # print("Данные успешно записаны в файл 'products_with_prices_and_brands.xlsx'")
    # else:
    #     print("Не удалось собрать данные.")

if __name__ == '__main__':
    main()