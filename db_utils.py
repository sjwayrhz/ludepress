"""数据库工具模块"""
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import logging
import time
from config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self):
        self.db_config = config.DB_CONFIG
    
    def _connect_with_retry(self):
        """带重试机制的数据库连接"""
        last_error = None
        
        for attempt in range(1, config.DB_MAX_RETRIES + 1):
            try:
                logger.debug(f"尝试连接数据库 (第{attempt}/{config.DB_MAX_RETRIES}次)")
                conn = pymysql.connect(**self.db_config, cursorclass=DictCursor)
                logger.debug("数据库连接成功")
                return conn
            except pymysql.err.OperationalError as e:
                last_error = e
                error_code = e.args[0] if e.args else 0
                
                # 2003: 无法连接到MySQL服务器
                # 2006: MySQL服务器已断开连接
                # 2013: 查询期间与MySQL服务器的连接丢失
                if error_code in (2003, 2006, 2013):
                    logger.warning(f"数据库连接失败 (尝试 {attempt}/{config.DB_MAX_RETRIES}): {e}")
                    
                    if attempt < config.DB_MAX_RETRIES:
                        wait_time = config.DB_RETRY_DELAY * attempt  # 指数退避
                        logger.info(f"等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"达到最大重试次数 ({config.DB_MAX_RETRIES})")
                else:
                    # 其他错误直接抛出
                    logger.error(f"数据库连接错误 (非网络问题): {e}")
                    raise
            except Exception as e:
                logger.error(f"数据库连接发生未知错误: {e}")
                raise
        
        # 所有重试都失败
        raise last_error
    
    def _ping_connection(self, conn):
        """检查并修复断开的连接"""
        try:
            conn.ping(reconnect=True)
        except Exception as e:
            logger.warning(f"连接ping失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = self._connect_with_retry()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作错误: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def create_tables(self):
        """创建数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建作者表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creators (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_name (name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # 创建分类表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_name (name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # 创建文章表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    guid VARCHAR(500) NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    link VARCHAR(1000) NOT NULL,
                    creator_id INT,
                    pub_date DATETIME,
                    description TEXT,
                    content LONGTEXT,
                    comments_link VARCHAR(1000),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_guid (guid(255)),
                    INDEX idx_pub_date (pub_date),
                    INDEX idx_creator_id (creator_id),
                    FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # 创建文章分类关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS article_categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    article_id INT NOT NULL,
                    category_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_article_category (article_id, category_id),
                    INDEX idx_article_id (article_id),
                    INDEX idx_category_id (category_id),
                    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            logger.info("数据库表创建成功")
    
    def get_or_create_creator(self, name: str) -> int:
        """获取或创建作者，返回作者ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 尝试获取现有作者
            cursor.execute("SELECT id FROM creators WHERE name = %s", (name,))
            result = cursor.fetchone()
            
            if result:
                return result['id']
            
            # 创建新作者
            cursor.execute("INSERT INTO creators (name) VALUES (%s)", (name,))
            return cursor.lastrowid
    
    def get_or_create_category(self, name: str) -> int:
        """获取或创建分类，返回分类ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 尝试获取现有分类
            cursor.execute("SELECT id FROM categories WHERE name = %s", (name,))
            result = cursor.fetchone()
            
            if result:
                return result['id']
            
            # 创建新分类
            cursor.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
            return cursor.lastrowid
    
    def insert_article(self, article_data: Dict[str, Any], categories: List[str]) -> Optional[int]:
        """插入文章数据"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查文章是否已存在
                cursor.execute("SELECT id FROM articles WHERE guid = %s", (article_data['guid'],))
                existing = cursor.fetchone()
                
                if existing:
                    logger.info(f"文章已存在: {article_data['title']}")
                    return existing['id']
                
                # 插入文章
                cursor.execute("""
                    INSERT INTO articles (guid, title, link, creator_id, pub_date, 
                                        description, content, comments_link)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    article_data['guid'],
                    article_data['title'],
                    article_data['link'],
                    article_data['creator_id'],
                    article_data['pub_date'],
                    article_data['description'],
                    article_data['content'],
                    article_data['comments_link']
                ))
                
                article_id = cursor.lastrowid
                
                # 插入分类关联
                for category_name in categories:
                    category_id = self.get_or_create_category(category_name)
                    cursor.execute("""
                        INSERT IGNORE INTO article_categories (article_id, category_id)
                        VALUES (%s, %s)
                    """, (article_id, category_id))
                
                logger.info(f"文章插入成功: {article_data['title']}")
                return article_id
                
        except Exception as e:
            logger.error(f"插入文章失败: {e}")
            return None
    
    def get_article_count(self) -> int:
        """获取文章总数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM articles")
            result = cursor.fetchone()
            return result['count'] if result else 0
    
    def get_category_stats(self) -> List[Dict[str, Any]]:
        """获取分类统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.name, COUNT(ac.article_id) as article_count
                FROM categories c
                LEFT JOIN article_categories ac ON c.id = ac.category_id
                GROUP BY c.id, c.name
                ORDER BY article_count DESC
            """)
            return cursor.fetchall()


# 创建全局数据库管理器实例
db_manager = DatabaseManager()
