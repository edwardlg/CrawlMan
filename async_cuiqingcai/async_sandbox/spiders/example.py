# -*- coding: utf-8 -*-
import datetime
import re

import scrapy
from scrapy import Request
import logging
from async_sandbox.items import AsyncSandboxItem
import redis
from scrapy.xlib.pydispatch import dispatcher
from scrapy import Request, signals
from scrapy.http.cookies import CookieJar


class ExampleSpider(scrapy.Spider):
    name = 'example'
    # 技术
    # BASE_URL = 'https://cuiqingcai.com/category/technique/page/{}'
    # 生活
    BASE_URL = 'https://cuiqingcai.com/category/life/page/{}'

    def start_requests(self):
        start_page = 1

        yield Request(
            url=self.BASE_URL.format(start_page),
            meta={'page': start_page},
            # dont_filter=True, 如果设置了true，并且在异常处理那里设置返回request，重新放入调度器，那么就会导致不断循环（假设错误不断发生）

        )

    def parse(self, response):

        cookie_obj = CookieJar()
        cookie_obj.extract_cookies(response,response.request)
        # print('cookie get ==================')
        # print(cookie_obj)
        # print(dir(cookie_obj))
        # print(cookie_obj._cookies) # 访问cookies
        # print('cookie end ===================')
        # print(response)
        page = response.meta['page']
        next_page = page + 1
        logging.info('on parse')
        logging.info(f'next page ========== {next_page}')
        articles = response.xpath('//article[@class="excerpt"]')
        for article in articles:
            item = AsyncSandboxItem()
            category = article.xpath('./header/a[1]/text()').extract_first()
            title = article.xpath('./header/h2/a[1]/text()').extract_first()
            article_url = article.xpath('./header/h2/a[1]/@href').extract_first()
            item['title'] = title
            item['category'] = category
            item['article_url'] = article_url

            yield Request(
                url=article_url,
                callback=self.parse_item,
                meta={'item': item}
            )

        if next_page < 900:
            yield Request(
                url=self.BASE_URL.format(next_page),
                meta={'page': next_page},
                # dont_filter=True
            )

    def parse_item(self, response):
        logging.info('in response parse_item')
        item = response.meta['item']
        author = response.xpath(
            '//header[@class="article-header"]//i[@class="fa fa-user"]/following::*[1]/text()').extract_first()
        visited = response.xpath(
            '//header[@class="article-header"]//i[@class="fa fa-eye"]/parent::*[1]/text()').extract_first()
        comment = response.xpath(
            '//header[@class="article-header"]//i[@class="fa fa-comments-o"]/following-sibling::*[1]/text()').extract_first()
        liked = response.xpath('//span[@class="count"]/text()').extract_first()
        created_at = response.xpath(
            '//header[@class="article-header"]//i[@class="fa fa-clock-o"]/parent::*[1]/text()').extract_first()
        content = response.xpath('//article[@class="article-content"]')[0].xpath('string(.)').extract()[0]

        item['author'] = author
        item['created_at'] = created_at
        # item['content'] = content
        visited=re.sub('浏览','',visited)
        item['visited'] = visited
        comment=re.sub('评论','',comment)
        item['comment'] = comment
        item['liked'] = liked
        item['crawltime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        yield item

class RedisSubcribe(scrapy.Spider):

    name = 'cuiqincai_chn'

    BASE_URL = 'https://cuiqingcai.com/category/technique/page/{}'

    def __init__(self,*args,**kwargs):
        super(RedisSubcribe,self).__init__(*args,**kwargs)

        # initial redis subscriber
        # pool = redis.ConnectionPool()
        self.conn = redis.Redis(host='10.18.6.46',decode_responses=True)
        self.subscribe_channel='cuiqingcai'
        self.pub = self.conn.pubsub()
        self.pub.subscribe(self.subscribe_channel)
        self.pub.parse_response()
        print('initial')

        self.timeout = 30
        dispatcher.connect(self.spider_idle, signals.spider_idle)


    # 订阅者模式 过期 掉线
    # def start_requests(self):
    #     # start_page = 0


    #     while 1:
    #         print('waiting for publish')
    #         msg = self.pub.parse_response()
    #         content = str(msg[2],'utf-8')
    #         print(content)

    #         if content=='0':
    #             break

    #         yield Request(
    #             url=self.BASE_URL.format(content),
    #             meta={'page': content},
    #             dont_filter=True,
    #         )
    #     yield None

    def start_requests(self):
        
        while 1:
            print('waiting for list')
            try:
                msg = self.conn.brpop('page_num',timeout=self.timeout) # 5分钟一次
            except Exception as e:
                print(e)
                self.conn = redis.Redis(host='10.18.6.46',decode_responses=True)
                msg = self.conn.brpop('page_num',timeout=self.timeout) # 5分钟一次
                
            
            if msg:
            
                page = msg[1]
                yield Request(
                url=self.BASE_URL.format(page),
                meta={'page': page},
                )

            else:
                print(f'waiting for receive data {datetime.datetime.now()}')

                self.conn = redis.Redis(host='10.18.6.46',decode_responses=True)


    def parse(self, response):

        page = response.meta['page']
        # print(response.status_code)
        print(response.text)
        
        if page ==0:
            print('get exit signal')
            exit()
        else:

            articles = response.xpath('//article[@class="excerpt"]')
            for article in articles:
                item = AsyncSandboxItem()
                category = article.xpath('./header/a[1]/text()').extract_first()
                title = article.xpath('./header/h2/a[1]/text()').extract_first()
                article_url = article.xpath('./header/h2/a[1]/@href').extract_first()
                item['title'] = title
                item['category'] = category
                item['article_url'] = article_url

                yield Request(
                url=article_url,
                callback=self.parse_item,
                meta={'item': item}
                )

    
    def parse_item(self, response):
        item = response.meta['item']
        author = response.xpath(
            '//header[@class="article-header"]//i[@class="fa fa-user"]/following::*[1]/text()').extract_first()
        visited = response.xpath(
            '//header[@class="article-header"]//i[@class="fa fa-eye"]/parent::*[1]/text()').extract_first()
        comment = response.xpath(
            '//header[@class="article-header"]//i[@class="fa fa-comments-o"]/following-sibling::*[1]/text()').extract_first()
        liked = response.xpath('//span[@class="count"]/text()').extract_first()
        created_at = response.xpath(
            '//header[@class="article-header"]//i[@class="fa fa-clock-o"]/parent::*[1]/text()').extract_first()
        content = response.xpath('//article[@class="article-content"]')[0].xpath('string(.)').extract()[0]

        item['author'] = author
        item['created_at'] = created_at
        # item['content'] = content
        visited=re.sub('浏览','',visited)
        item['visited'] = visited
        comment=re.sub('评论','',comment)
        item['comment'] = comment
        item['liked'] = liked
        item['crawltime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        yield item

    # 设置idle的时候
    def spider_idle(self, spider):

        print('idle status , try go to visit')
        raise DontCloseSpider("Stayin' alive")

class RabbitMQSpider(scrapy.Spider):
    name = 'cuiqincai'
    BASE_URL = 'https://cuiqingcai.com/category/technique/page/{}'

    def start_requests(self):
        home = 'https://cuiqingcai.com/'
        yield Request(
                url=home
            )

    def parse(self,response):


    def __init__(self,*args,**kwargs):
        super(RabbitMQSpider,self).__in

        credentials = pika.PlainCredentials('guest','guest')

        connection = pika.BlockingConnection(pika.ConnectionParameters('10.18.6.46',5672,'/',credentials))

        queue_name='spider'

        self.channel = connection.channel()
        self.channel.queue_declare(queue=queue_name, durable=True)


        self.channel.basic_consume(
            on_message_callback=self.callback,
            queue=queue_name,
            auto_ack=True,
            )


    def send_mail(self):
        pass

    def callback(self,ch,method,properties,body):
        content = str(body,encoding='utf8')
        print('[x] received body {}'.format(content))
        js_content = json.loads(content)
        self.send_mail()


    def start(self):
        print('[*] waiting for the message, to exit press Ctrl+C')

        self.channel.start_consuming()