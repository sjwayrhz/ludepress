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
try:
    import lxml
except ImportError:
    pass

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
            # 先用requests获取feed内容（带超时控制）
            response = self.session.get(feed_url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # 使用feedparser解析获取到的内容
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"Feed解析警告: {feed.bozo_exception}")
            
            articles = []
            for entry in feed.entries:
                article = self._extract_article_from_entry(entry)
                if article:
                    articles.append(article)
            
            logger.info(f"从RSS feed解析到 {len(articles)} 篇文章")
            return articles
            
        except requests.Timeout:
            logger.error(f"请求RSS feed超时 (>{config.REQUEST_TIMEOUT}秒): {feed_url}")
            return []
        except requests.RequestException as e:
            logger.error(f"请求RSS feed失败: {e}")
            return []
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
    
    def parse_sitemap_index(self, sitemap_url: str = None) -> List[str]:
        """解析sitemap索引，返回所有sub-sitemap URLs"""
        if sitemap_url is None:
            sitemap_url = config.SITEMAP_URL
        
        logger.info(f"解析sitemap索引: {sitemap_url}")
        
        try:
            response = self.session.get(sitemap_url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            sitemap_urls = []
            
            # 查找所有sitemap标签
            for sitemap in soup.find_all('sitemap'):
                loc = sitemap.find('loc')
                if loc and 'post-sitemap' in loc.text:
                    sitemap_urls.append(loc.text)
            
            logger.info(f"发现 {len(sitemap_urls)} 个文章sitemap")
            return sitemap_urls
            
        except Exception as e:
            logger.error(f"解析sitemap索引失败: {e}")
            return []
    
    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """解析单个sitemap，返回所有文章URLs"""
        logger.info(f"解析sitemap: {sitemap_url}")
        
        try:
            response = self.session.get(sitemap_url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            article_urls = []
            
            # 查找所有url标签
            for url in soup.find_all('url'):
                loc = url.find('loc')
                if loc:
                    article_urls.append(loc.text)
            
            logger.info(f"从sitemap获取 {len(article_urls)} 篇文章URL")
            return article_urls
            
        except Exception as e:
            logger.error(f"解析sitemap失败: {e}")
            return []
    
    def get_all_article_urls_from_sitemap(self) -> List[str]:
        """从sitemap获取所有文章URLs"""
        all_urls = []
        
        # 1. 获取所有sub-sitemaps
        sitemap_urls = self.parse_sitemap_index()
        
        # 2. 解析每个sitemap
        for sitemap_url in sitemap_urls:
            urls = self.parse_sitemap(sitemap_url)
            all_urls.extend(urls)
            time.sleep(config.SLEEP_BETWEEN_REQUESTS)
        
        logger.info(f"从sitemap总共获取 {len(all_urls)} 篇文章URL")
        return all_urls
    
    def scrape_all_feeds(self):
        """爬取所有feed（包括归档）"""
        all_articles = []
        
        # 1. 爬取主feed
        logger.info("开始爬取主RSS feed")
        articles = self.parse_rss_feed()
        all_articles.extend(articles)
        
        # 2. 尝试分页feed (WordPress通常支持 /feed/?paged=2 格式)
        page = 2
        max_pages = config.MAX_FEED_PAGES
        
        # 如果设置了页数限制，显示提示信息
        if max_pages > 0:
            logger.info(f"最大爬取页数限制: {max_pages} 页")
        else:
            logger.info("无页数限制，将爬取所有可用feed页面")
        
        while True:
            # 检查是否达到页数限制（max_pages为0表示无限制）
            if max_pages > 0 and page > max_pages:
                logger.info(f"已达到最大页数限制 ({max_pages} 页)，停止爬取")
                break
            
            feed_url = f"{self.feed_url}?paged={page}"
            logger.info(f"尝试爬取第 {page} 页feed")
            
            articles = self.parse_rss_feed(feed_url)
            if not articles:
                logger.info(f"第 {page} 页没有文章，停止分页爬取")
                break
            
            all_articles.extend(articles)
            time.sleep(config.SLEEP_BETWEEN_REQUESTS)
            page += 1  # 增加页码
        
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
    
    def scrape_article_from_url(self, url: str) -> Dict[str, Any]:
        """从URL直接爬取文章详情（用于补充sitemap中缺失的文章）"""
        try:
            response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取文章数据
            article = {
                'guid': url,
                'link': url,
                'title': '',
                'content': '',
                'description': '',
                'creator': '',
                'pub_date': datetime.now(),
                'categories': [],
                'comments_link': ''
            }
            
            # 提取标题
            title_tag = soup.find('h1', class_='entry-title') or soup.find('h1')
            if title_tag:
                article['title'] = title_tag.get_text(strip=True)
            
            # 提取内容
            content_tag = soup.find('div', class_='entry-content') or soup.find('article')
            if content_tag:
                article['content'] = content_tag.get_text(strip=True)
                article['description'] = article['content'][:200]
            
            # 提取作者
            author_tag = soup.find('span', class_='author') or soup.find('a', rel='author')
            if author_tag:
                article['creator'] = author_tag.get_text(strip=True)
            
            # 提取分类
            category_tags = soup.find_all('a', rel='category tag')
            article['categories'] = [cat.get_text(strip=True) for cat in category_tags]
            
            # 提取日期
            time_tag = soup.find('time', class_='entry-date')
            if time_tag and time_tag.get('datetime'):
                try:
                    article['pub_date'] = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                except:
                    pass
            
            return article
            
        except Exception as e:
            logger.error(f"从URL爬取文章失败 {url}: {e}")
            return None
    
    def run(self):
        """运行爬虫主流程"""
        logger.info("=" * 50)
        logger.info("开始运行路德社爬虫")
        logger.info("=" * 50)
        
        # 1. 初始化数据库
        logger.info("初始化数据库...")
        db_manager.create_tables()
        
        # 2. 从RSS Feed批量爬取文章（优先，效率高）
        logger.info("步骤1: 从RSS Feed批量爬取文章...")
        articles = self.scrape_all_feeds()
        logger.info(f"从RSS Feed爬取到 {len(articles)} 篇文章")
        
        # 3. 保存RSS文章到数据库
        if articles:
            logger.info("保存RSS文章到数据库...")
            self.save_articles_to_db(articles)
        
        # 4. 从Sitemap获取所有文章URL（确保完整性）
        logger.info("步骤2: 从Sitemap发现所有文章URL...")
        all_urls = self.get_all_article_urls_from_sitemap()
        logger.info(f"Sitemap中共有 {len(all_urls)} 篇文章")
        
        # 5. 检查哪些文章还未在数据库中
        logger.info("步骤3: 检查缺失的文章...")
        missing_count = 0
        
        # 批量检查缺失的URL（使用分批查询优化性能）
        existing_urls = set()
        
        if all_urls:
            # 分批查询，避免单次查询参数过多导致性能问题
            batch_size = 1000
            total_batches = (len(all_urls) + batch_size - 1) // batch_size
            
            logger.info(f"开始检查 {len(all_urls)} 个URL，分为 {total_batches} 批处理")
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                for i in range(0, len(all_urls), batch_size):
                    batch_urls = all_urls[i:i + batch_size]
                    batch_num = i // batch_size + 1
                    
                    logger.info(f"检查第 {batch_num}/{total_batches} 批 ({len(batch_urls)} 个URL)")
                    
                    # 使用 link 字段查询（因为 sitemap 中的 URL 对应 articles.link）
                    placeholders = ','.join(['%s'] * len(batch_urls))
                    query = f"SELECT link FROM articles WHERE link IN ({placeholders})"
                    cursor.execute(query, batch_urls)
                    
                    batch_existing = cursor.fetchall()
                    for article in batch_existing:
                        existing_urls.add(article['link'])
                
                # 找出缺失的URLs
                missing_urls = [url for url in all_urls if url not in existing_urls]
                logger.info(f"检查完成: 已存在 {len(existing_urls)} 篇，缺失 {len(missing_urls)} 篇")
        
        # 爬取缺失的文章
        for url in missing_urls:
            missing_count += 1
            logger.info(f"爬取缺失文章 ({missing_count}/{len(missing_urls)}): {url}")
            article = self.scrape_article_from_url(url)
            if article:
                self.save_articles_to_db([article])
            time.sleep(config.SLEEP_BETWEEN_REQUESTS)
        
        logger.info(f"补充爬取了 {missing_count} 篇缺失文章")
        
        # 6. 显示统计信息
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
