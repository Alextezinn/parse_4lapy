"""
Да есть куда улучшаться можно запросы сделать асинхронными, отрефакторить код,
тесты написать.
"""
import json
from typing import Union, NewType

import requests
from bs4 import BeautifulSoup


ProductInfo = NewType('ProductInfo', dict[str, Union[list[dict[str, any]], str]])

all_products = []

code_cities = {
    #'Санкт-Петербург': '0000103664',
    'Москва': '0000073738'
}


def get_count_pages(soup: BeautifulSoup) -> int:
    count_pages = soup.find('ul', class_='b-pagination__list').find_all('li')[-2].find('a').get_text().replace("\n", "").strip()
    return int(count_pages)

def parse_category():
    response = requests.get("https://4lapy.ru/catalog/koshki/korm-koshki/sukhoy/?section_id=3&sort=popular&page=1")
    soup = BeautifulSoup(response.text, 'lxml')
    count_pages = get_count_pages(soup)

    for page in range(1, count_pages + 1):
        print(f"Парсится страница {page}")
        page_products = {}
        response = requests.get(f"https://4lapy.ru/catalog/koshki/korm-koshki/sukhoy/?section_id=3&sort=popular&page={page}")
        soup = BeautifulSoup(response.text, 'lxml')
        html_products = soup.find_all('div', class_='b-common-item b-common-item--catalog-item js-product-item')

        for html_product in html_products:
            product_id = html_product.get('data-productid')
            url = html_product.find('a', class_='b-common-item__image-link js-item-link')
            url = url['href'].split('?')[0]
            page_products[product_id] = {'url': url, 'offers': []}

        param_product = [f"product[]={product}" for product in page_products]
        param_product = "&".join(param_product)
        response = requests.get(
            f"https://4lapy.ru/ajax/catalog/product-info?section_id=3&sort=popular&page={page}&{param_product}")
        products = response.json()

        for product in products['data']['products']:
            page_products[product]['offers'] = list(products['data']['products'][product]['offers'].keys())

        all_products.append(page_products)

    for city_name, code_city in code_cities.items():
        print(f"Парсятся товары с города {city_name}")
        city_products = parse_category_city(code_city)
        write_products_json(city_name, city_products)


def parse_category_city(code_city: str) -> list[ProductInfo]:
    "Парсинг категории по конкретному городу"
    info_products = []

    for page_products in all_products:
        for product in page_products:
            for offer in page_products[product]['offers']:
                response = requests.get(
                    f"https://4lapy.ru/ajax/delivery/common-pickup/calculate-location-shops/{code_city}/offer/{offer}")
                print(f"Парсится товар с {offer=}")
                product_quantity_and_addresses = []
                g_parts_available = None

                for item in response.json()['features']:
                    calculated_shop = item['properties']['calculated_shop']

                    try:
                        parts_available = calculated_shop['parts_available'][0]
                    except Exception as e:
                        parts_available = calculated_shop['parts_available']

                    if not parts_available:
                        continue

                    quantity = parts_available['quantity']

                    if parts_available and g_parts_available is None:
                        g_parts_available = parts_available

                    if quantity < 1:
                        continue

                    product_quantity_and_addresses.append(
                        {
                            'address': calculated_shop['adress'],
                            'quantity': quantity
                        }
                    )

                else:
                    if g_parts_available is None:
                        continue

                    brend, name = g_parts_available['name'].split("</strong>")
                    brend = brend.replace("<strong>", "").strip()
                    name = name.strip()
                    url = "https://4lapy.ru" + page_products[product]['url'] + f"?offer={offer}"

                    info_products.append({
                        'id': g_parts_available['id'],
                        'name': name,
                        'url': url,
                        'price': g_parts_available['price'],
                        'old_price': g_parts_available['old_price'],
                        'vendor_code': g_parts_available['xmlId'],
                        'brend': brend,
                        'shops': product_quantity_and_addresses
                    })

    return info_products


def write_products_json(filename: str, city_products: list[ProductInfo]) -> None:
    with open(f"{filename}.json", "w") as file:
        json.dump({'products': city_products}, file, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    parse_category()
