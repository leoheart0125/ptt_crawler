import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from bs4 import BeautifulSoup
from bs4.element import NavigableString
import json
import os
import time
import datetime
import re
from dateutil.parser import parse as parsedate
from fake_useragent import UserAgent
import var 

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
session = requests.session()
session.post("https://www.ptt.cc/ask/over18", data={"yes": "yes"})

#取得熱門看板
def get_hotboards():
    url = "https://www.ptt.cc/bbs/hotboards.html"
    r = session.get(url)
    soup = BeautifulSoup(r.text,"html.parser")
    boards = soup.select("a.board")
    return boards
#取得網頁header中的最後更新時間並轉成unix time
def get_last_modified(url):
    r = requests.head(url)
    dt = parsedate(r.headers['Date'])
    last_modified_at = int(time.mktime(dt.timetuple()))*1000
    return last_modified_at
#過濾特殊字符(目前用不到)
def remove_punctuation(line):
    rule = re.compile(r"[^a-zA-Z0-9\u4e00-\u9fa5\u0020-\u002f\u003a-\u0040]")
    line = rule.sub('',line)
    return line
#取得爬取該網頁的時間並轉成unix time
def get_crawltime():
    dtime = datetime.datetime.now()
    ans_time = round(time.mktime(dtime.timetuple()))
    return ans_time*1000
#將爬取內容寫出json檔(沒用到)
def ouput_board_page_articles_json(filename , res):
    if not os.path.exists("/ptt_crawler/PPT_Crawler/PPT_Crawl_Result2"):
        os.makedirs("/ptt_crawler/PPT_Crawler/PPT_Crawl_Result2")
    with open("/ptt_crawler/PPT_Crawler/PPT_Crawl_Result2/" + filename + ".json" , 'wb') as f:
        f.write(json.dumps(res, indent = 4, ensure_ascii = False).encode('utf-8'))
#取得Ptt該篇貼文的發文時間並轉成unix time
def get_unixtime(time_string):
    month_vector = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
    month = month_vector[time_string[4:7]]
    year = time_string[-4:]
    #print(len(time_string))
    day = time_string[8:10]
    day = day.replace(" ","")
    ptime = time_string[11:19]
    publish_time = year+"-"+str(month)+"-"+day+" "+ptime
    print(publish_time)
    unixtime = round(time.mktime(datetime.datetime.strptime(publish_time, '%Y-%m-%d %H:%M:%S').timetuple()))
    return unixtime*1000

#上傳額外連結至server
def insert_links(data):
    try:
        token_data = {
            "account": var.account,
            "password":var.password
        }
        token_response = requests.post(var.base_url+"users", json=token_data).json()
        token=token_response['token']
        post_headers = { 'Authorization': 'Bearer '+token}
        response = requests.post(var.base_url+"links", headers=post_headers, json=data)
        print(response.json())
    except Exception as e:
        print(e)
    
#新增category
def insert_category(data):
    try:
        token_data = {
            "account": var.account,
            "password":var.password
        }
        token_response = requests.post(var.base_url+"users", json=token_data).json()
        token=token_response['token']
        post_headers = { 'Authorization': 'Bearer '+token}
        response = requests.post(var.base_url+"categorylist", headers=post_headers, json=data)
        print(response.json())
    except Exception as e:
        print(e)

#爬取該篇貼文    
def get_content(article_url):
    ua = UserAgent(use_cache_server=False)
    ua_headers = {"User-Agent": ua.random}
    r = session.get(article_url,headers=ua_headers)
    soup = BeautifulSoup(r.text, "html.parser")
    if r.status_code==404:
        return
    a_tags = soup.find_all('a')
    extra_links=[]#初始化額外連結陣列
    
    ###爬取所有URL(只抓https開頭，過濾掉local路徑)，如果domain不是ptt.cc就上傳###
    for tag in a_tags:
        url = tag.get("href")
        try:
            if url.split(':')[0] == "https":
                domain = url.split('/')[2]
                if not domain == "www.ptt.cc":
                      extra_links.append(url)
        except Exception as e:
            print(e)
    if len(extra_links) > 0:
        insert_links(extra_links)
    try:
        article = {}
        article['language'] = "ZH_TW"
        article['crawled_at'] = get_crawltime()
        article['Author'] = soup.select('.article-meta-value')[0].text
        article['category'] = "PTT_"+article_url.split("/")[4]
        article['title'] = soup.select('.article-meta-value')[2].text
        article['publish_at'] = get_unixtime(soup.select('.article-meta-value')[3].text)
        article['link'] = article_url
        article['last_modified_at'] = get_last_modified(article_url)
        content = []
        article['contents'] = r.text
        
    except Exception as e:
        print(e)
        print("Analysis %s occur Error" %article_url )

    try:
        token_data = {
            "account": var.account,
            "password":var.password
        }
        token_response = requests.post(var.base_url+"users", json=token_data).json()
        token=token_response['token']
        post_headers = { 'Authorization': 'Bearer '+token}
        response = requests.post(var.base_url+"ptt", headers=post_headers
                                 , json=json.dumps(article))
        print(response.json())
        #將結果寫入logfile
        filename = article_url.split("/")[4]+"_"+(article_url.split("/")[5]).split(".")[1]
        with open(var.logfile_path,"a")as ptt_log:
            log_msg = str(get_crawltime()) + " " + filename +"\n"+str(response.json())+"\n"
            ptt_log.write(log_msg)
    except Exception as e:
        print(e)

#取得看板該頁的所有貼文連結並且呼叫get_content()
def get_all_href(url):
    r = session.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    results = soup.select("div.title")
    for item in results:
        a_item = item.select_one("a")
        title = item.text
        if a_item:
            print(title, 'https://www.ptt.cc'+ a_item.get('href'))
            get_content('https://www.ptt.cc'+  a_item.get('href'))

urls = get_hotboards() #取得熱門看板URL
for boards in urls:
    url = "https://www.ptt.cc"+boards['href']
    categorylist = {"term":"","description":""}
    category = boards["href"].split("/")[2]
    categorylist["term"] = "PTT_"+category
    categorylist["description"] = "PTT_"+category
    insert_category(categorylist)
    print(url)
    r = session.get(url)
    soup = BeautifulSoup(r.text,"html.parser")
    btn = soup.select('div.btn-group > a')
    up_page_href = btn[3]['href']
    pages = ((up_page_href.split("/")[3]).split(".")[0]).split("index")[1] #該看板總頁數
    total_page = int(pages)
    for page in range(total_page - var.crawl_pages,total_page):
        url = "https://www.ptt.cc/bbs/"+category+"/index"+str(page)+".html"
        print(url)
        get_all_href(url)#看板URL傳入get_all_href()