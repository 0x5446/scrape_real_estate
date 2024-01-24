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
import math
import re



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
    driver = webdriver.Remote(
        command_executor='http://selenium-chrome-debug:4444/wd/hub',
        options=chrome_options
    )
    return driver


# 配置WebDriver
driver_zf = configure_driver()

links_zf_file = './output/links_zf.idx'
csv_zf = './output/zf.csv'
url_zf_base = 'https://bj.zu.ke.com'


def get_all_zf_entrypoint():
    if os.path.exists(links_zf_file) and os.path.getsize(links_zf_file) > 0:
        with open(links_zf_file, 'r', encoding='utf-8') as file:
            links = [line.strip() for line in file.readlines()]
            return links

    base_url = 'https://bj.zu.ke.com/zufang/rt200600000001' 
    driver_zf.get(base_url)
    elements = driver_zf.find_elements(By.XPATH, "//li[@data-type='district']/a")

    hrefs = []
    links = []
    # 遍历元素并获取href
    for element in elements:
        if element.text.strip() == '不限':
            continue
        href = element.get_attribute('href')
        hrefs.append(href)

    for href in hrefs:
        driver_zf.get(href)
        eles = driver_zf.find_elements(By.XPATH, "//li[@data-type='bizcircle']/a")
        for e in eles:
            if e.text.strip() == '不限':
                continue
            links.append(e.get_attribute('href'))

    with open(links_zf_file, 'w', encoding='utf-8') as file:
        file.write('\n'.join(links))

    return links


def parse_html(html):
    """解析HTML页面并提取所需数据"""
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find_all('div', class_='content__list--item')
    if soup.find('div', class_='content__empty1'):
        return []
    data = []
    for item in items:
        title_tag = item.find('p', class_='content__list--item--title')
        title = title_tag.a.get_text().strip()
        link = url_zf_base + title_tag.a['href']

        des_tag = item.find('p', class_='content__list--item--des')

        a_tags = des_tag.find_all('a')
        if a_tags:  # 检查是否存在a标签
            community_id = a_tags[-1]['href'].split('/')[-2].lstrip('c')
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

def get_paged_url(url: str, n: int):
    if n < 2:
        return url

    parts = url.split('/')
    # 确定要修改的部分的索引
    index = -2 if parts[-1] == '' else -1

    # 检查该部分是否已经以 'pg' 加数字开始
    if re.match(r'^pg\d+', parts[index]):
        # 仅替换 'pg' 后面的数字部分
        parts[index] = re.sub(r'(?<=pg)\d+', str(n), parts[index])
    else:
        # 添加 'pg' 和数字
        parts[index] = 'pg' + str(n) + parts[index]

    # 重新组合 URL 部分
    return '/'.join(parts)

def scrape_zf():
    all_links = get_all_zf_entrypoint()
    n_links = len(all_links)
    i_links = 0 #如果脚本中断，此处可设置断点i_links-1继续作业，最终文件数据请手动去重sort |uniq > newfile
    for url_zf_list in all_links[i_links:]:
        i_links += 1
        n = 1

        driver_zf.get(url_zf_list)
        html = driver_zf.page_source
        data_zf = parse_html(html)
        if not data_zf:
            print(f'Link: {i_links}/{n_links} {url_zf_list} has no data, try next link')
            continue
        save_to_csv(data_zf, csv_zf)

        k = int(driver_zf.find_element(By.XPATH, '//span[@class="content__title--hl"]').text.strip())
        m = math.ceil(k / 30)

        print(f'Link: {i_links}/{n_links} {url_zf_list}; {k} items, {m} pages to scrape')
        print(f'Scrape ZF data page:{n} sucessfully!')
        n = n + 1

        while n <= m:
            url_zf_list = get_paged_url(url_zf_list, n)
            driver_zf.get(url_zf_list)
            html = driver_zf.page_source
            data_zf = parse_html(html)
            if not data_zf:
                print(f'Page {n}/{m} is empty, stop paging')
                break 
            save_to_csv(data_zf, csv_zf)

            print(f'Scrape ZF data page:{n} sucessfully!')
            n = n + 1

scrape_zf()