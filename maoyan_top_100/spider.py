#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author: wangfp time:2017/11/3

"""
爬取猫眼网站TOP100的电影信息
"""

import re, json
from multiprocessing import Pool

import requests
from requests.exceptions import RequestException

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}


def get_one_page(url):
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.text
    except RequestException as e:
        return e.reason


def parse_one_page(html):
    # pattern = re.compile('<dd>.*?board-index.*?>(.*?)</i>.*?data-src="(.*?)"', re.S)
    pattern = re.compile('<dd>.*?board-index.*?>(.*?)</i>.*?data-src="(.*?)".*?'
                         + 'name"><a.*?>(.*?)</a>.*?star">(.*?)</p>.*?releasetime">(.*?)</p>'
                         + '.*?integer">(.*?)</i>.*?fraction">(.*?)</i>.*?</dd>', re.S)
    results = re.findall(pattern, html)
    for result in results:
        yield {
            'index': result[0],
            'image': result[1],
            'name': result[2],
            # 汉字的切片？
            'star': result[3].strip()[3:],
            'release_date': result[4].strip()[5:],
            'score': result[5] + result[6]
        }


def write(content):
    # 确保以汉字的形式写入
    # 使用追加模式
    with open('maoyan_top_100.txt', 'a', encoding='utf-8') as f:
        f.write(json.dumps(content, ensure_ascii=False) + '\n')


def main(offset=0):
    url = 'http://maoyan.com/board/4' + '?offset=' + str(offset)
    html = get_one_page(url)
    for result in parse_one_page(html):
        print(result)
        write(result)


if __name__ == '__main__':
    pool = Pool()
    # 进程池的两种处理方法
    # pool.map(main, (10*i for i in range(10)))
    for i in range(10):
        pool.apply_async(main, args=(10*i,))
    pool.close()
    pool.join()
