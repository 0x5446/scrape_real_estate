# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import os, sys
import csv
import time



def configure_driver():
    """配置Selenium WebDriver."""
    chrome_options = Options()
    # 设置自定义用户代理
    chrome_options.add_argument("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    # 设置接受语言
    chrome_options.add_argument("accept-language=en-US,en;q=0.9")
    # 设置窗口大小
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("--disable-dev-shm-usage")
    #chrome_options.add_argument("--headless")
    #chrome_options.add_argument("--disable-gpu")
    #chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    # 连接到Docker容器中的Selenium
    driver1 = webdriver.Remote(
        command_executor='http://selenium-chrome-debug:4444/wd/hub',
        options=chrome_options
    )
    driver2 = webdriver.Remote(
        command_executor='http://selenium-chrome-debug:4444/wd/hub',
        options=chrome_options
    )
    return driver1, driver2



csv_zf = './output/zf.csv'
url_zf_base = 'https://bj.zu.ke.com'

def gen_url_zf_list(n: int):
    return 'https://bj.zu.ke.com/zufang/' + ('pg' + str(n) if n > 1 else '') + 'rt200600000001#contentList'


def parse_html(html):
    """解析HTML页面并提取所需数据"""
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find_all('div', class_='content__list--item')
    data = []
    for item in items:
        title_tag = item.find('p', class_='content__list--item--title')
        title = title_tag.a.get_text().strip()
        link = url_zf_base + title_tag.a['href']

        des_tag = item.find('p', class_='content__list--item--des')

        a_tags = des_tag.find_all('a')
        if a_tags:  # 检查是否存在a标签
            community_id = a_tags[-1]['href'].split('/')[-1]
        else:
            continue;
        
        details = [d.strip() for d in des_tag.get_text(strip=True).split('/') if d.strip()]

        # 检查是否有足够的数据，如果没有，则跳过这个项目
        if len(details) < 5:
            print('details columns are less than 5', file=sys.stderr)
            continue

        community = details[-5]
        size = details[-4]
        orientation = details[-3]
        layout = details[-2]
        layer_info = [p.strip() for p in details[-1].split()]
        floors = layer_info[1].replace("（", "").replace("）", "") if len(layer_info) > 1 else 0
        layer = layer_info[0]

        price_tag = item.find('span', class_='content__list--item-price')
        price = price_tag.get_text(strip=True)
        price = price.replace('元/月', '')

        data.append({
            'title': title,
            'link': link,
            'community_id': community_id,
            'community': community,
            'size': size,
            'orientation': orientation,
            'layout': layout,
            'layer': layer,
            'floors': floors,
            'price': price
        })
    return data


def save_to_csv(data, file_path):
    """将数据保存到CSV文件"""
    with open(file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        if os.stat(file_path).st_size == 0:
            writer.writeheader()
        for row in data:
            writer.writerow(row)


# 配置WebDriver
driver_zf, driver_esf = configure_driver()

# 访问租房列表页面
def scrape_zf():
    n = 1
    while True:
        url_zf_list = gen_url_zf_list(n)
        driver_zf.get(url_zf_list)
        time.sleep(5)  # 等待页面加载

        # 获取页面源码
        html = driver_zf.page_source

        # 解析HTML并提取数据
        rental_data = parse_html(html)

        if not rental_data:
            print('Scrape ZF data completed!')
            break;

        # 将数据保存到CSV文件
        save_to_csv(rental_data, csv_zf)
        
        print(f'Scrape ZF data page:{n} sucessfully!')
        n = n + 1

scrape_zf()