import csv
import time
from dataclasses import dataclass, fields
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = "https://webscraper.io/"
HOME_URL = urljoin(BASE_URL, "test-sites/e-commerce/more/")


_driver: WebDriver | None = None


def get_driver() -> WebDriver:
    global _driver
    if _driver is None:
        _driver = webdriver.Chrome()
    return _driver


def accept_cookies(driver: WebDriver):
    try:
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "acceptCookies"))
        )
        cookie_button.click()
    except:
        pass  # Якщо плашки немає, йдемо далі


def set_driver(new_driver: WebDriver) -> None:
    global _driver
    _driver = new_driver


def click_more_button(driver: WebDriver):
    while True:
        try:
            # Шукаємо кнопку "More" - це <a> тег з класом .ecomerce-items-scroll-more
            more_buttons = driver.find_elements(
                By.CSS_SELECTOR, ".ecomerce-items-scroll-more"
            )

            if not more_buttons:
                break

            more_button = more_buttons[0]

            # Scroll to button if needed
            driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
            time.sleep(0.3)

            # Click using JavaScript (more reliable)
            driver.execute_script("arguments[0].click();", more_button)

            # Wait for products to load
            time.sleep(1)

        except:
            # Якщо кнопки немає або вона не натискається — виходимо з циклу
            break


@dataclass
class Product:
    title: str
    description: str
    price: float
    rating: int
    num_of_reviews: int

    @classmethod
    def from_csv_row(cls, row: list[str]) -> "Product":
        """Parse Product from CSV row with proper type conversion"""
        return cls(
            title=row[0],
            description=row[1],
            price=float(row[2]),
            rating=int(row[3]),
            num_of_reviews=int(row[4]),
        )


def parse_page(driver: WebDriver) -> list[Product]:
    products = []
    # Чекаємо появи хоча б одного товару
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "thumbnail"))
    )

    items = driver.find_elements(By.CLASS_NAME, "thumbnail")
    for item in items:
        try:
            # Намагаємось знайти усі поля, з fallback значеннями
            title = item.find_element(By.CLASS_NAME, "title").get_attribute("title")
            description = item.find_element(By.CLASS_NAME, "description").text
            price_text = item.find_element(By.CLASS_NAME, "price").text.replace("$", "")
            price = float(price_text)

            # Спробуємо знайти рейтинг різними способами
            rating = 0
            try:
                # Спосіб 1: Пошук p[data-rating]
                rating = int(
                    item.find_element(By.CSS_SELECTOR, "p[data-rating]").get_attribute(
                        "data-rating"
                    )
                )
            except:
                try:
                    # Спосіб 2: Підрахунок іконок зірок
                    stars = item.find_elements(By.CSS_SELECTOR, "p .ws-icon-star")
                    rating = len(stars)
                except:
                    rating = 0  # Default if not found

            # Спробуємо знайти кількість відзивів
            try:
                num_of_reviews_text = item.find_element(
                    By.CLASS_NAME, "review-count"
                ).text
                num_of_reviews = int(num_of_reviews_text.split()[0])
            except:
                num_of_reviews = 0  # Default if not found

            products.append(
                Product(
                    title=title,
                    description=description,
                    price=price,
                    rating=rating,
                    num_of_reviews=num_of_reviews,
                )
            )
        except Exception as e:
            # Пропускаємо товари з помилками при парсингу
            print(f"Помилка при парсингу товару: {e}")
            continue

    return products


PAGES = {
    "home": HOME_URL,
    "computers": urljoin(HOME_URL, "computers"),
    "laptops": urljoin(HOME_URL, "computers/laptops"),
    "tablets": urljoin(HOME_URL, "computers/tablets"),
    "phones": urljoin(HOME_URL, "phones"),
    "touch": urljoin(HOME_URL, "phones/touch"),
}


def get_all_products():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Опціоналка №1: без вікна

    with webdriver.Chrome(options=options) as driver:
        for page_name, url in PAGES.items():
            print(f"Scraping {page_name}...")
            driver.get(url)
            accept_cookies(driver)  # Викликаємо для кожної сторінки

            click_more_button(driver)  # Тиснемо "More", поки є
            products = parse_page(driver)

            write_products_to_csv(products, f"{page_name}.csv")


def write_products_to_csv(products: list[Product], filename: str) -> None:
    # Дістаємо назви полів з dataclass для заголовка CSV
    field_names = [f.name for f in fields(Product)]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(field_names)
        for product in products:
            writer.writerow(
                [
                    product.title,
                    product.description,
                    product.price,
                    product.rating,
                    product.num_of_reviews,
                ]
            )


def main():
    get_all_products()


if __name__ == "__main__":
    main()
