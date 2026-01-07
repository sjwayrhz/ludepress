# 路德社网站爬虫项目

这是一个用于爬取 ludepress.com 网站内容并存入 MySQL 数据库的 Python 爬虫项目。

## 功能特点

- ✅ **完整覆盖**：基于sitemap发现所有3643篇文章
- ✅ **混合爬取策略**：优先使用RSS Feed批量获取，补充sitemap缺失文章
- ✅ 自动提取文章分类并存储
- ✅ 数据库自动去重（基于GUID）
- ✅ 支持MySQL SSL加密连接
- ✅ 支持增量更新
- ✅ 详细的日志记录
- ✅ 环境变量配置管理
- ✅ Python 3.12 支持


## 数据库结构

项目包含以下数据表：

1. **creators** - 作者表
2. **categories** - 分类表
3. **articles** - 文章表
4. **article_categories** - 文章分类关联表

## 安装步骤

### 1. 克隆项目

```bash
cd ludepress
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置数据库连接

在项目根目录创建 `.env` 文件（参考 `.env.example`）：

```bash
# MySQL数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=ludepress_db

# MySQL SSL配置（可选）
# 如果您的MySQL服务器需要SSL加密连接，请取消注释并配置以下选项
# DB_SSL_ENABLED=true
# DB_SSL_CA=/path/to/ca-cert.pem
# DB_SSL_CERT=/path/to/client-cert.pem
# DB_SSL_KEY=/path/to/client-key.pem
```

**注意**：爬虫配置（如BASE_URL、FEED_URL等）已硬编码在 `config.py` 中，无需在 `.env` 文件中配置。

### 5. 创建数据库

在 MySQL 中创建数据库：

```sql
CREATE DATABASE ludepress_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 使用方法

### 运行爬虫

```bash
python scraper.py
```

爬虫将：
1. 自动创建数据库表结构
2. **步骤1**：从RSS Feed批量爬取文章（高效获取元数据和内容）
3. **步骤2**：从sitemap发现所有3643篇文章URL
4. **步骤3**：检查并补充爬取RSS中缺失的文章
5. 自动保存到MySQL数据库（自动去重）
6. 输出统计信息和分类统计

### 查看日志

运行日志会同时输出到控制台和 `scraper.log` 文件。

## 文件说明

- `scraper.py` - 主爬虫脚本
- `db_utils.py` - 数据库操作工具
- `config.py` - 配置管理模块
- `.env` - 环境变量配置（需自行创建）
- `.env.example` - 环境变量配置模板
- `requirements.txt` - Python 依赖包
- `.gitignore` - Git 忽略文件配置

## 分类说明

系统会自动从 RSS feed 中提取以下分类并存储：

- 路德时评
- 闫博士说
- 糯贴
- 墨文
- 要闻
- 美国
- 中共情资
- 国际
- 播客
- 讨论区
- Featured
- 简讯
- 快讯
- 等等...

## 注意事项

1. **数据库权限**：确保 MySQL 用户有足够的权限创建表和插入数据
2. **网络连接**：爬虫需要稳定的网络连接访问 ludepress.com
3. **爬取频率**：代码中已设置请求间隔，避免对服务器造成压力
4. **数据去重**：系统会自动检测重复文章（基于 GUID），避免重复插入

## 故障排除

### 1. 数据库连接失败

检查 `.env` 文件中的数据库配置是否正确，确保 MySQL 服务已启动。

### 2. 编码问题

确保数据库和表使用 `utf8mb4` 字符集，以正确存储中文内容。

### 3. 依赖安装失败

尝试升级 pip：

```bash
python -m pip install --upgrade pip
```

然后重新安装依赖。

## 开发信息

- **Python 版本**：3.12
- **数据库**：MySQL 5.7+
- **字符编码**：UTF-8

## 许可证

本项目仅供学习和研究使用。

## 贡献

欢迎提交 Issue 和 Pull Request。