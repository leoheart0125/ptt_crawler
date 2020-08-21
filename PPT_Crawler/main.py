from ptt_crawler import Crawler

def main():
    
    crawler = Crawler()
    crawler.crawl(board = "Gossiping", start_page = 3000, end_page = 3001)

if __name__ == '__main__':
    main()