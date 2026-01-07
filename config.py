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
        'charset': 'utf8mb4'
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
    
    # 用户代理
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


# 导出配置实例
config = Config()
