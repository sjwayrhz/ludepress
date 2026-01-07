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
    
    # 爬虫配置
    BASE_URL = os.getenv('BASE_URL', 'https://ludepress.com')
    FEED_URL = os.getenv('FEED_URL', 'https://ludepress.com/feed/')
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))
    RETRY_TIMES = int(os.getenv('RETRY_TIMES', 3))
    SLEEP_BETWEEN_REQUESTS = float(os.getenv('SLEEP_BETWEEN_REQUESTS', 1))
    
    # 用户代理
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


# 导出配置实例
config = Config()
