"""查看文章和分类的对应关系"""
from db_utils import db_manager

print("=" * 80)
print("文章和分类对应关系查询")
print("=" * 80)

with db_manager.get_connection() as conn:
    cursor = conn.cursor()
    
    # 方式1: 查询每篇文章及其所属的分类
    print("\n【方式1: 查询前10篇文章及其分类】")
    print("-" * 80)
    
    query = """
        SELECT 
            a.id,
            a.title,
            a.pub_date,
            GROUP_CONCAT(c.name ORDER BY c.name SEPARATOR ', ') as categories
        FROM articles a
        LEFT JOIN article_categories ac ON a.id = ac.article_id
        LEFT JOIN categories c ON ac.category_id = c.id
        GROUP BY a.id, a.title, a.pub_date
        ORDER BY a.pub_date DESC
        LIMIT 10
    """
    
    cursor.execute(query)
    articles = cursor.fetchall()
    
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. 文章ID: {article['id']}")
        print(f"   标题: {article['title'][:60]}...")
        print(f"   发布日期: {article['pub_date']}")
        print(f"   分类: {article['categories'] or '(无分类)'}")
    
    # 方式2: 查询特定分类下的文章数量
    print("\n\n【方式2: 查询每个分类下的文章数量】")
    print("-" * 80)
    
    query = """
        SELECT 
            c.id,
            c.name,
            COUNT(ac.article_id) as article_count
        FROM categories c
        LEFT JOIN article_categories ac ON c.id = ac.category_id
        GROUP BY c.id, c.name
        ORDER BY article_count DESC
    """
    
    cursor.execute(query)
    category_stats = cursor.fetchall()
    
    for stat in category_stats:
        print(f"{stat['name']:15s} (ID: {stat['id']:2d}): {stat['article_count']:4d} 篇文章")
    
    # 方式3: 查看article_categories关联表的详细内容
    print("\n\n【方式3: article_categories关联表示例(前20条)】")
    print("-" * 80)
    
    query = """
        SELECT 
            ac.id,
            ac.article_id,
            a.title,
            ac.category_id,
            c.name as category_name
        FROM article_categories ac
        JOIN articles a ON ac.article_id = a.id
        JOIN categories c ON ac.category_id = c.id
        ORDER BY ac.id DESC
        LIMIT 20
    """
    
    cursor.execute(query)
    relations = cursor.fetchall()
    
    print(f"\n{'关联ID':<8} {'文章ID':<8} {'分类ID':<8} {'分类名称':<15} 文章标题")
    print("-" * 80)
    for rel in relations:
        title = rel['title'][:40] + "..." if len(rel['title']) > 40 else rel['title']
        print(f"{rel['id']:<8} {rel['article_id']:<8} {rel['category_id']:<8} {rel['category_name']:<15} {title}")
    
    # 统计信息
    print("\n\n【数据库统计信息】")
    print("-" * 80)
    
    cursor.execute("SELECT COUNT(*) as count FROM articles")
    article_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM categories")
    category_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM article_categories")
    relation_count = cursor.fetchone()['count']
    
    print(f"文章总数: {article_count}")
    print(f"分类总数: {category_count}")
    print(f"文章-分类关联总数: {relation_count}")
    print(f"平均每篇文章的分类数: {relation_count/article_count:.2f}" if article_count > 0 else "N/A")

print("\n" + "=" * 80)
