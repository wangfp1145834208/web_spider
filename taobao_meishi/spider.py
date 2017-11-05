#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author: wangfp time:2017/11/4

"""
通过selenium来模拟浏览器加载网页，这样可以避免繁琐的ajax请求
1.不同浏览器需要不同的驱动器
2.pyquery对页面的分析
3.如何确保网页的完全加载——WebDriverWait()函数的使用及加载条件判断（看官方文档）
"""

import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from pyquery import PyQuery as pq
import pymongo

from config import *

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]

# br = webdriver.Chrome()
# 使用PhantomJS可以不用弹出浏览器
br = webdriver.PhantomJS(service_args=SERVICE_ARGS)
wait = WebDriverWait(br, 10)

br.set_window_size(1400, 900)


def search():
    print('正在搜索。。。')
    try:
        br.get('https://www.taobao.com')
        # 等待并判断加载完成
        search_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#q'))
        )
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#J_TSearchForm > div.search-button > button'))
        )
        search_input.send_keys(KEYWORD)
        submit.click()
        total = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total')))
        # 页面加载成功后进行页面分析
        page_parse()
        return total.text
    except TimeoutException:
        return search()


def next_page(index):
    try:
        index_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > input'))
        )
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit'))
        )
        # 首先清除搜索框中的内容
        index_input.clear()
        index_input.send_keys(index)
        submit.click()
        # 通过与当前页面（高亮显示）值进行比较来确定该页面是否已经加载完成
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'), str(index)))
        # 页面加载成功后进行页面分析
        page_parse()
    except TimeoutException:
        next_page(index)


def page_parse():
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-itemlist')))
    html = br.page_source
    doc = pq(html)
    items = doc('#mainsrp-itemlist .items .item').items()
    for item in items:
        # 如果标签中再无其它文本内容，就不需要更为精确的定位
        product = {
            'image': item.find('.pic .img').attr('src'),
            'price': item.find('.price').text(),
            'deal': item.find('.deal-cnt').text()[:-3],
            'title': item.find('.title').text(),
            'shop': item.find('.shop').text(),
            'location': item.find('.location').text(),
        }
        save_to_mongo(product)


def save_to_mongo(result):
    try:
        if db[MONGO_TABLE].insert(result):
            print('储存到MONGODB成功', result)
    except Exception:
        print('储存失败', result)


def main():
    # 确保浏览器的关闭
    try:
        total = search()
        total = int(re.search('(\d+)', total).group(1))
        print('总共%d页' % total)
        page_start = int(input('爬取起始页码：'))
        page_end = int(input('爬取结束页码：'))
        for i in range(page_start, page_end+1):
            print('正在爬取第%d页数据' % i)
            next_page(i)
    finally:
        br.close()
    print('爬取完成！')


if __name__ == '__main__':
    main()

