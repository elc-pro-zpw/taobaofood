import re
from lxml import etree
import pymongo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By  #选择条件
from selenium.webdriver.support.ui import WebDriverWait #浏览器等待加载
from selenium.webdriver.support import expected_conditions as EC   #希望的选择条件，即通过什么判断加载成功了
import urllib.parse as parse
from selenium.common.exceptions import TimeoutException  #导入的异常类
from setting import *
import logging

class taobao:
	def __init__(self,keyword):	
		options = Options()   #声明一个无头浏览器
		options.add_argument('-headless')
		self.keyword = keyword
		self.browser = webdriver.Chrome(chrome_options=options)
		self.client = pymongo.MongoClient(MONGOURL,27017)
		self.tb = self.client[MONGODB]    #初始化数据库
		self.meishi = self.tb[MONGOSHEET]

	def get_one_page(self):
		try:
			# url = 'http://uland.taobao.com/sem/tbsearch?keyword=%E7%BE%8E%E9%A3%9F&page=0'
			url = 'https://www.taobao.com/'
			self.browser.get(url)
			self.wait = WebDriverWait(self.browser,10)
			element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#q')))  #浏览器等待10s直到希望的元素出现了（通过id或其它找到了），里面的选择元素是个元祖
			submit = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,'#J_TSearchForm > div.search-button > button')))
			element.send_keys(self.keyword)
			submit.click()
			next_page = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#mainsrp-pager > div > div > div > div.total')))
			return next_page.text
		except TimeoutException:
			return self.get_one_page()

	def get_totalpage(self,text):
		page = re.findall('(\d+)',text)
		return int(page[0])

	def next_page(self,i):
		try:
			inp = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#mainsrp-pager > div > div > div > div.form > input')))
			bottou = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,'#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit')))
			inp.clear() #先清除之前的内容
			inp.send_keys(i)
			bottou.click()
			#等待文本出现在当前元素中
			self.wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR,'#mainsrp-pager > div > div > div > ul > li.item.active > span'),str(i)))
		except TimeoutException:
			self.next_page(i) #如果出现超时错误，再次递归调用

	def get_products(self):
		self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#mainsrp-itemlist .items')))
		html = self.browser.page_source
		tree = etree.HTML(html)    #lxml库有cssselect、xpath选择器，还有find(类似BeautifulSoup)的选择器，非常强大！！
		items = tree.cssselect('#mainsrp-itemlist .items .item')
		for i in items:
			products = {
				'img':i.cssselect('.pic>a>img')[0].get('data-src'),
				'title':i.cssselect('.pic>a>img')[0].get('alt'),
				'price':i.cssselect('.price')[0].xpath('string(.)').strip(),   #选择所有的文本，特殊方法，还有[starts-with('class','shop')]
				'shop':i.cssselect(".shopname")[0].xpath('string(.)').strip(),
				'location':i.cssselect('.location')[0].text,
				}
			print(products)
			yield products

	def save_to_mongo(self):
		for product in self.get_products():
			try:
				if self.meishi.insert(product):
					print('数据插入到mongodb成功！')
			except Exception as er:
				print(er)

	def main(self):
		total = self.get_one_page()
		totalnum = self.get_totalpage(total)
		for i in range(2,totalnum+1):
			self.next_page(i)
			self.save_to_mongo()
		self.browser.close()

if __name__ == '__main__':
	logging.basicConfig(filename='taobao.log',filemode='a',level=logging.ERROR,format='%(asctime)s%(message)s',datefmt='%Y%m%d%I:%M:%S:%p')
	tao = taobao('美食')
	tao.main()