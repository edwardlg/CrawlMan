# -*-coding=utf-8-*-

# @Time : 2018/9/26 9:58
# @File : run.py

from scrapy import cmdline
name = 'gaode1'
cmd = 'scrapy crawl {}'.format(name)
cmdline.execute(cmd.split())