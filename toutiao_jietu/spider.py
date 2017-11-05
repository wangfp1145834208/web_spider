#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author: wangfp time:2017/11/3

"""
通过对ajax的请求来解析并下载今日头条的街拍图片
使用到了：
1.mongoDB的连接
2.JSON格式内容的解析
3.配置文件的创造
4.多进程
"""

import re, json, os, time
from urllib.parse import urlencode
from hashlib import md5
from multiprocessing import Pool

import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
import pymongo

from config import *

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}

DIR_NAME = time.strftime('%m-%d-%H', time.gmtime())
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), DIR_NAME)

# 由于用到多进程，所以将connect参数设置为False
client = pymongo.MongoClient(MONGO_URL, connect=False)
db = client[MONGO_DB]


# 通过请求ajax获取所需内容
# 头条中的ajax大多数是GET请求
def get_page_index(offset, keyword):
    # data为通过GET请求的数据
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 3,
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.text
        # 或者直接返回resp.json()这一json格式
    except RequestException:
        print('请求页面出错')


def parse_page_index(html):
    data = json.loads(html)
    if data['data']:
        for item in data.get('data'):
            yield item.get('article_url')


def get_page_detail(url):
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.text
    except RequestException:
        print('请求%s详情页面出错' % url)


def parse_page_detail(detail, url):
    soup = BeautifulSoup(detail, 'lxml')
    title = soup.select('title')[0].get_text()
    images_pattern = re.compile(r'gallery: (.*)')
    images_url = re.search(images_pattern, detail)
    if images_url:
        # 去掉匹配中的逗号之后才能进行json.loads()操作
        data = json.loads(images_url.group(1)[:-1])
        if data['sub_images']:
            sub_images = data.get('sub_images')
            # 对字典的解析很重要
            images = [item.get('url_list')[0].get('url') for item in sub_images]
            for image in images:
                download_image(image)
            return {'title': title,
                    'url': url,
                    'images': images}


def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储成功', result)
        return True
    return False


def download_image(url):
    print('正在下载：', url)
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            save_image(resp.content)
    except RequestException:
        print('请求%s图片出错' % url)


def save_image(content):
    # 通过md5进行不重复命名
    file_name = '{0}.{1}'.format(md5(content).hexdigest(), 'jpg')
    file_path = os.path.join(BASE_DIR, file_name)
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content)


def main(offset):
    html = get_page_index(offset, KEYWORD)
    t = 1
    for url in parse_page_index(html):
        detail = get_page_detail(url)
        result = parse_page_detail(detail, url)
        save_to_mongo(result)
        if t == 1:
            break


if __name__ == '__main__':
    if not os.path.isdir(BASE_DIR):
        os.mkdir(BASE_DIR)
    groups = [20*offset for offset in range(GROUP_START, GROUP_END + 1)]
    p = Pool()
    p.map(main, groups)
