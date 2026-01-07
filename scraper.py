"""路德社网站爬虫主模块"""
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
import time
import logging
from urllib.parse import urljoin, urlparse
import re

from config import config
from db_utils import db_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LudepressScraper:
    """路德社网站爬虫类"""
    
    def __init__(self):
        self.base_url = config.BASE_URL
        self.feed_url = config.FEED_URL
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.USER_AGENT})
    
    def parse_rss_feed(self, feed_url: str = None) -> List[Dict[str, Any]]:
        """解析RSS feed"""
        if feed_url is None:
            feed_url = self.feed_url
        
        logger.info(f"开始解析RSS feed: {feed_url}")
        
        try:
            # 使用feedparser解析RSS
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logger.warning(f"Feed解析警告: {feed.bozo_exception}")
            
            articles = []
            for entry in feed.entries:
                article = self._extract_article_from_entry(entry)
                if article:
                    articles.append(article)
            
            logger.info(f"从RSS feed解析到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logger.error(f"解析RSS feed失败: {e}")
            return []
    
    def _extract_article_from_entry(self, entry) -> Dict[str, Any]:
        """从RSS entry提取文章数据"""
        try:
            # 提取基本信息
            article = {
                'title': entry.get('title', ''),
                'link': entry.get('link', ''),
                'guid': entry.get('id', entry.get('link', '')),
                'pub_date': self._parse_date(entry.get('published', '')),
                'description': self._clean_html(entry.get('summary', '')),
                'content': self._clean_html(entry.get('content', [{}])[0].get('value', '')) if entry.get('content') else '',
                'comments_link': entry.get('comments', ''),
                'creator': entry.get('author', ''),
                'categories': []
            }
            
            # 提取分类
            if hasattr(entry, 'tags'):
                article['categories'] = [tag.term for tag in entry.tags]
            
            return article
            
        except Exception as e:
            logger.error(f"提取文章数据失败: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """解析日期字符串"""
        try:
            # feedparser已经解析了日期
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            return datetime.now()
    
    def _clean_html(self, html_content: str) -> str:
        """清理HTML内容"""
        if not html_content:
            return ''
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # 移除脚本和样式
            for script in soup(['script', 'style']):
                script.decompose()
            return soup.get_text(strip=True)
        except:
            return html_content
    
    def fetch_article_content(self, url: str) -> str:
        """获取文章完整内容"""
        try:
            response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 尝试查找文章内容区域
            # 根据WordPress常见结构查找
            content = None
            for selector in ['.entry-content', '.post-content', 'article', '.content']:
                content = soup.select_one(selector)
                if content:
                    break
            
            if content:
                # 移除不需要的元素
                for tag in content.find_all(['script', 'style', 'iframe']):
                    tag.decompose()
                return content.get_text(strip=True)
            
            return ''
            
        except Exception as e:
            logger.error(f"获取文章内容失败 {url}: {e}")
            return ''
    
    def discover_archive_pages(self) -> List[str]:
        """发现归档页面URL"""
        archive_urls = []
        
        try:
            # WordPress标准归档格式
            # 尝试获取最新页面的日期范围
            response = self.session.get(self.base_url, timeout=config.REQUEST_TIMEOUT)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找归档链接
            for link in soup.find_all('a', href=True):
                href = link['href']
                # 匹配日期归档URL: /2025/01/, /2024/12/ 等
                if re.search(r'/\d{4}/\d{2}/?', href):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in archive_urls:
                        archive_urls.append(full_url)
            
            # 也可以构造分页URL
            # 例如: /page/2/, /page/3/ 等
            for page_num in range(2, 20):  # 假设最多20页
                page_url = f"{self.base_url}/page/{page_num}/"
                archive_urls.append(page_url)
            
            logger.info(f"发现 {len(archive_urls)} 个归档页面")
            return archive_urls
            
        except Exception as e:
            logger.error(f"发现归档页面失败: {e}")
            return []
    
    def scrape_all_feeds(self):
        """爬取所有feed（包括归档）"""
        all_articles = []
        
        # 1. 爬取主feed
        logger.info("开始爬取主RSS feed")
        articles = self.parse_rss_feed()
        all_articles.extend(articles)
        
        # 2. 尝试分页feed (WordPress通常支持 /feed/?paged=2 格式)
        for page in range(2, 50):  # 尝试前50页
            feed_url = f"{self.feed_url}?paged={page}"
            logger.info(f"尝试爬取第 {page} 页feed")
            
            articles = self.parse_rss_feed(feed_url)
            if not articles:
                logger.info(f"第 {page} 页没有文章，停止分页爬取")
                break
            
            all_articles.extend(articles)
            time.sleep(config.SLEEP_BETWEEN_REQUESTS)
        
        return all_articles
    
    def save_articles_to_db(self, articles: List[Dict[str, Any]]):
        """保存文章到数据库"""
        success_count = 0
        
        for article in articles:
            try:
                # 获取或创建作者
                creator_id = None
                if article.get('creator'):
                    creator_id = db_manager.get_or_create_creator(article['creator'])
                
                # 准备文章数据
                article_data = {
                    'guid': article['guid'],
                    'title': article['title'],
                    'link': article['link'],
                    'creator_id': creator_id,
                    'pub_date': article['pub_date'],
                    'description': article['description'],
                    'content': article['content'],
                    'comments_link': article.get('comments_link', '')
                }
                
                # 插入文章和分类
                if db_manager.insert_article(article_data, article.get('categories', [])):
                    success_count += 1
                
                time.sleep(0.1)  # 避免数据库压力
                
            except Exception as e:
                logger.error(f"保存文章失败 {article.get('title', 'Unknown')}: {e}")
        
        logger.info(f"成功保存 {success_count}/{len(articles)} 篇文章")
        return success_count
    
    def run(self):
        """运行爬虫主流程"""
        logger.info("=" * 50)
        logger.info("开始运行路德社爬虫")
        logger.info("=" * 50)
        
        # 1. 初始化数据库
        logger.info("初始化数据库...")
        db_manager.create_tables()
        
        # 2. 爬取所有文章
        logger.info("开始爬取文章...")
        articles = self.scrape_all_feeds()
        logger.info(f"共爬取到 {len(articles)} 篇文章")
        
        # 3. 保存到数据库
        if articles:
            logger.info("开始保存文章到数据库...")
            self.save_articles_to_db(articles)
        
        # 4. 显示统计信息
        total_articles = db_manager.get_article_count()
        logger.info(f"数据库中共有 {total_articles} 篇文章")
        
        category_stats = db_manager.get_category_stats()
        logger.info("分类统计:")
        for stat in category_stats[:10]:  # 显示前10个分类
            logger.info(f"  {stat['name']}: {stat['article_count']} 篇")
        
        logger.info("=" * 50)
        logger.info("爬虫运行完成")
        logger.info("=" * 50)


def main():
    """主函数"""
    scraper = LudepressScraper()
    scraper.run()


if __name__ == '__main__':
    main()
