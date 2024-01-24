# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import csv
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

links_esf_file = './output/links_esf.idx'
csv_esf = './output/esf.csv'
url_esf_base = 'https://bj.ke.com'


def get_all_esf_entrypoint():
    if os.path.exists(links_esf_file) and os.path.getsize(links_esf_file) > 0:
        with open(links_esf_file, 'r', encoding='utf-8') as file:
            links = [line.strip() for line in file.readlines()]
            return links

    base_url = 'https://bj.ke.com/ershoufang/' 
    driver.get(base_url)
    elements = driver.find_elements(By.XPATH, "//a[@data-click-evtid='12339']")

    hrefs = []
    links = []
    # 遍历元素并获取href
    for element in elements:
        href = element.get_attribute('href')
        hrefs.append(href)

    for href in hrefs:
        driver.get(href)
        eles = driver.find_elements(By.XPATH, "//div[@data-role='ershoufang']/div[2]/a")
        for e in eles:
            links.append(e.get_attribute('href'))

    with open(links_esf_file, 'w', encoding='utf-8') as file:
        file.write('\n'.join(links))

    return links


def parse_html():
    eles_li = driver.find_elements(By.XPATH, "//ul[@class='sellListContent']/li[@class='clear']")
    if not eles_li:
        return []
    data = []
    for li in eles_li:
        a = li.find_element(By.XPATH, ".//a[@class='VIEWDATA CLICKDATA maidian-detail']")
        title = a.text.strip()
        link = a.get_attribute('href')

        a = li.find_element(By.XPATH, ".//div[@class='positionInfo']/a")
        community = a.text.strip()
        community_id = a.get_attribute('href').split('/')[-2]

        info = li.find_element(By.XPATH, ".//div[@class='houseInfo']").text.strip()

        price_total = li.find_element(By.XPATH, ".//div[@class='totalPrice totalPrice2']/span").text.strip()
        price_unit = li.find_element(By.XPATH, ".//div[@class='unitPrice']/span").text.strip()

        data.append({
            'title': title,
            'link': link,
            'community_id': community_id,
            'community': community,
            'info': info,
            'price_total': price_total,
            'price_unit': price_unit
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

    # 检查 URL 是否以 '/' 结尾
    if url.endswith('/'):
        url = url[:-1]

    # 检查 URL 最后部分是否已经是 'pg' 加数字
    if re.search(r'pg\d+$', url):
        # 替换 'pg' 后面的数字
        url = re.sub(r'pg\d+$', f'pg{n}', url)
    else:
        # 追加 '/pg' 和数字
        url += f'/pg{n}'

    return url

def scrape_esf():
    all_links = get_all_esf_entrypoint()
    n_links = len(all_links)
    i_links = 0 #如果脚本中断，此处可设置断点i_links-1继续作业，最终文件数据请手动去重sort |uniq > newfile
    for url_esf_list in all_links[i_links:]:
        i_links += 1
        n = 1

        driver.get(url_esf_list)
        data_esf = parse_html()
        if not data_esf:
            print(f'Link: {i_links}/{n_links} {url_esf_list} has no data, try next link')
            continue
        save_to_csv(data_esf, csv_esf)

        k = int(driver.find_element(By.XPATH, '//h2[@class="total fl"]/span').text.strip())
        m = math.ceil(k / 30)

        print(f'Link: {i_links}/{n_links} {url_esf_list}; {k} items, {m} pages to scrape')
        print(f'Scrape esf data page:{n} sucessfully!')
        n = n + 1

        while n <= m:
            url_esf_list = get_paged_url(url_esf_list, n)
            driver.get(url_esf_list)
            data_esf = parse_html()
            if not data_esf:
                print(f'Page {n}/{m} is empty, stop paging')
                break 
            save_to_csv(data_esf, csv_esf)

            print(f'Scrape esf data page:{n} sucessfully!')
            n = n + 1

scrape_esf()