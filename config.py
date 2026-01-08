"""配置管理模块"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """配置类"""
    
    # 数据库配置
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'ludepress_db'),
        'charset': 'utf8mb4',
        'connect_timeout': 10,  # 连接超时（秒）
        'read_timeout': 30,     # 读超时（秒）
        'write_timeout': 30,    # 写超时（秒）
        'autocommit': False     # 手动控制事务
    }
    
    # MySQL SSL配置
    DB_SSL_ENABLED = os.getenv('DB_SSL_ENABLED', 'false').lower() == 'true'
    DB_SSL_CA = os.getenv('DB_SSL_CA', '')
    DB_SSL_CERT = os.getenv('DB_SSL_CERT', '')
    DB_SSL_KEY = os.getenv('DB_SSL_KEY', '')
    
    # 如果启用SSL，添加SSL配置到DB_CONFIG
    if DB_SSL_ENABLED:
        ssl_config = {}
        if DB_SSL_CA:
            ssl_config['ca'] = DB_SSL_CA
        if DB_SSL_CERT:
            ssl_config['cert'] = DB_SSL_CERT
        if DB_SSL_KEY:
            ssl_config['key'] = DB_SSL_KEY
        
        if ssl_config:
            DB_CONFIG['ssl'] = ssl_config
        else:
            # 如果只启用SSL但没有指定证书，使用默认SSL验证
            DB_CONFIG['ssl'] = {'ssl': True}
    
    # 爬虫配置（硬编码常量）
    BASE_URL = 'https://ludepress.com'
    FEED_URL = 'https://ludepress.com/feed/'
    SITEMAP_URL = 'https://ludepress.com/sitemap.xml'
    REQUEST_TIMEOUT = 30
    RETRY_TIMES = 3
    SLEEP_BETWEEN_REQUESTS = 1
    MAX_FEED_PAGES = int(os.getenv('MAX_FEED_PAGES', '0'))  # 最大爬取feed页数，0表示无限制
    
    # 网站主分类白名单(只保存这些分类,其他标签忽略)
    MAIN_CATEGORIES = {
        'Featured',
        '专栏评论',
        '中共情资',
        '军事',
        '国会',
        '国际',
        '地缘',
        '墨文',
        '报道',
        '简讯',
        '糯贴',
        '美国',
        '要闻',
        '路德时评',
        '闫博士说'
    }
    
    # 数据库重试配置
    DB_MAX_RETRIES = 3  # 最大重试次数
    DB_RETRY_DELAY = 2  # 重试间隔(秒)
    
    # 用户代理
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


# 导出配置实例
config = Config()
