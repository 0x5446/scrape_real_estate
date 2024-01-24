# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
driver = configure_driver()

links_zf_file = './output/links_zf.idx'
csv_zf = './output/zf.csv'
url_zf_base = 'https://bj.zu.ke.com'


def get_all_zf_entrypoint():
    if os.path.exists(links_zf_file) and os.path.getsize(links_zf_file) > 0:
        with open(links_zf_file, 'r', encoding='utf-8') as file:
            links = [line.strip() for line in file.readlines()]
            return links

    base_url = 'https://bj.zu.ke.com/zufang/rt200600000001' 
    driver.get(base_url)
    elements = driver.find_elements(By.XPATH, "//li[@data-type='district']/a")

    hrefs = []
    links = []
    # 遍历元素并获取href
    for element in elements:
        if element.text.strip() == '不限':
            continue
        href = element.get_attribute('href')
        hrefs.append(href)

    for href in hrefs:
        driver.get(href)
        eles = driver.find_elements(By.XPATH, "//li[@data-type='bizcircle']/a")
        for e in eles:
            if e.text.strip() == '不限':
                continue
            links.append(e.get_attribute('href'))

    with open(links_zf_file, 'w', encoding='utf-8') as file:
        file.write('\n'.join(links))

    return links


def parse_html():

    data = []

    list = driver.find_elements(By.XPATH, "//div[@class='content__list']/div[@data-el='listItem']")
    
    i = 0
    n = len(list)
    for div in list:    
        i += 1
        a = div.find_element(By.XPATH, ".//div[@class='content__list--item--main']//a[1]")
        title = a.text.strip()
        link = a.get_attribute('href')

        info = div.find_element(By.XPATH, ".//p[@class='content__list--item--des']")

        a = info.find_elements(By.XPATH, ".//a")
        if a:  # 检查是否存在a标签
            community_id = a[-1].get_attribute('href').split('/')[-2].lstrip('c')
        else:
            continue;

        community = '-'.join([i.text.strip() for i in a])
        
        info = [e.strip() for e in info.text.strip().split('/') if e.strip()]

        if len(info) < 3:
            print(f'Info items less than 3, parse next. {1}/{n}@current_url:{driver.current_url}', file=sys.stderr)
            continue

        orientation = size = layout = ''
        for e in info:
            if re.search(r"[东南西北]", e):
                orientation = e
            elif e.endswith("㎡"):
                size = e
            elif re.search(r"\d.*?(室|厅|卫|房间)", e):
                layout = e

        if not size:
            print(f'no size, parse next. {1}/{n}@current_url:{driver.current_url}', file=sys.stderr)
            continue

        info = '|'.join(info)
        price = div.find_element(By.XPATH, ".//span[@class='content__list--item-price']/em").text.strip()

        data.append({
            'title': title,
            'link': link,
            'community_id': community_id,
            'community': community,
            'info': info,
            'size': size,
            'orientation': orientation,
            'layout': layout,
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

        driver.get(url_zf_list)
        html = driver.page_source
        data_zf = parse_html()
        if not data_zf:
            print(f'Link: {i_links}/{n_links} {url_zf_list} has no data, try next link')
            continue
        save_to_csv(data_zf, csv_zf)

        k = int(driver.find_element(By.XPATH, '//span[@class="content__title--hl"]').text.strip())
        m = math.ceil(k / 30)

        print(f'Link: {i_links}/{n_links} {url_zf_list}; {k} items, {m} pages to scrape')
        print(f'Scrape ZF data page:{n} sucessfully!')
        n = n + 1

        while n <= m:
            url_zf_list = get_paged_url(url_zf_list, n)
            driver.get(url_zf_list)
            html = driver.page_source
            data_zf = parse_html()
            if not data_zf:
                print(f'Page {n}/{m} is empty, stop paging')
                break 
            save_to_csv(data_zf, csv_zf)

            print(f'Scrape ZF data page:{n} sucessfully!')
            n = n + 1

scrape_zf()