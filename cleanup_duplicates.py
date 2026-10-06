#!/usr/bin/env python3
"""ludepress 数据库清理脚本：删除老地址僵尸行 + link 重复行。

背景：网站改过 URL 结构（如 /dryan/47468/ 301 到 /ytchannels/dryan/47468/），
sitemap 只收新地址。补漏爬取后库里同时存在老地址行和新地址行，总数会超过
sitemap 的 9717。本脚本做三类清理（方案已由用户 2026-10-06 确认）：

1. 老地址僵尸行：link 不在当前 sitemap 中的行，逐个请求——
   - 301/302 跳转且最终地址在 sitemap（内容已在新地址入库）→ 删除老行
   - 404 → 删除
   - 200（还能正常打开）→ 保留
   - 请求失败/跳转到 sitemap 之外 → 保留并记入待人工复核
2. link 完全重复：同一 link 多行，只保留 id 最小（最早插入）的一行。
3. news-type 等其它老格式：走同样的"请求看状态"规则（301 且目标在 sitemap、
   或 404 → 删；200 → 留）。

前提：必须在爬虫补漏跑完（sitemap 新地址全部入库）之后再执行，否则会误删。

用法（在项目目录、clerk 上跑，.env 需配好）：
  python cleanup_duplicates.py            # dry-run：只打印将要删除的行，不动库
  python cleanup_duplicates.py --apply    # 真正执行删除
"""
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import config
from db_utils import db_manager
from scraper import LudepressScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cleanup.log', encoding='utf-8'),
    ],
    force=True,
)
logger = logging.getLogger(__name__)

APPLY = '--apply' in sys.argv
MAX_WORKERS = 6  # HTTP 检查并发数


def norm(url: str) -> str:
    return url.strip().rstrip('/')


def check_url(url: str):
    """请求单个 URL，返回 (action, reason, final_url)。

    action: 'delete' / 'keep' / 'review'
    """
    try:
        resp = requests.get(
            url,
            headers={'User-Agent': config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT,
            allow_redirects=True,
        )
    except Exception as e:
        return 'review', f'请求失败: {type(e).__name__} {e}', url

    if resp.status_code == 404:
        return 'delete', '404 已失效', url

    if resp.history:
        codes = [h.status_code for h in resp.history]
        final = resp.url
        return 'redirect', f'跳转 {codes} -> {final}', final

    if resp.status_code == 200:
        return 'keep', '200 仍可正常打开', url

    return 'review', f'异常状态码 {resp.status_code}', url


def main():
    logger.info('=' * 50)
    logger.info(f'开始数据库清理（{"APPLY 真实删除" if APPLY else "DRY-RUN 预演"}）')
    logger.info('=' * 50)

    # 0. 拉取当前 sitemap，作为"有效地址"基准（失败直接退出，不误删）
    scraper = LudepressScraper()
    try:
        sitemap_urls = scraper.get_all_article_urls_from_sitemap()
    except Exception as e:
        logger.error(f'✗ sitemap 获取失败，无法确定基准，退出: {e}')
        sys.exit(1)
    sitemap_set = {norm(u) for u in sitemap_urls}
    logger.info(f'sitemap 基准: {len(sitemap_set)} 个 URL')

    to_delete = []   # (id, link, reason)
    review = []      # (id, link, reason)

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        # 1. link 完全重复：只留最早插入的一行
        logger.info('阶段1: 检查 link 完全重复…')
        cursor.execute("""
            SELECT link, COUNT(*) AS c, MIN(id) AS keep_id,
                   GROUP_CONCAT(id ORDER BY id) AS ids
            FROM articles
            GROUP BY link
            HAVING c > 1
        """)
        dup_groups = cursor.fetchall()
        logger.info(f'发现 {len(dup_groups)} 组重复 link')
        for g in dup_groups:
            keep = g['keep_id']
            ids = [int(x) for x in g['ids'].split(',')]
            for i in ids:
                if i != keep:
                    to_delete.append((i, g['link'], f'link 重复，保留最早 id={keep}'))

        # 2. 找出 link 不在 sitemap 中的候选行（老地址僵尸行）
        logger.info('阶段2: 找出 link 不在 sitemap 中的候选行…')
        cursor.execute("SELECT id, link, title FROM articles")
        all_rows = cursor.fetchall()
        logger.info(f'数据库共 {len(all_rows)} 行')

    candidates = [r for r in all_rows if norm(r['link']) not in sitemap_set]
    # 排除阶段1已标记删除的行
    doomed_ids = {d[0] for d in to_delete}
    candidates = [r for r in candidates if r['id'] not in doomed_ids]
    logger.info(f'候选老地址行: {len(candidates)} 行（link 不在 sitemap）')

    # 3. 并发请求每个候选 URL 看状态
    logger.info(f'阶段3: 逐个请求候选 URL（{MAX_WORKERS} 并发）…')
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_to_row = {pool.submit(check_url, r['link']): r for r in candidates}
        for fut in as_completed(future_to_row):
            row = future_to_row[fut]
            done += 1
            if done % 100 == 0:
                logger.info(f'  已检查 {done}/{len(candidates)}')
            action, reason, final_url = fut.result()
            if action == 'delete':
                to_delete.append((row['id'], row['link'], reason))
            elif action == 'redirect':
                if norm(final_url) in sitemap_set:
                    to_delete.append(
                        (row['id'], row['link'],
                         f'{reason}；目标在 sitemap，已有新地址行'))
                else:
                    review.append(
                        (row['id'], row['link'],
                         f'{reason}；目标不在 sitemap，人工复核'))
            elif action == 'keep':
                logger.debug(f'保留 id={row["id"]}: {reason} {row["link"]}')
            else:  # review
                review.append((row['id'], row['link'], reason))

    # 4. 汇总
    logger.info('=' * 50)
    logger.info(f'待删除: {len(to_delete)} 行；待人工复核: {len(review)} 行')
    for _id, link, reason in to_delete[:50]:
        logger.info(f'  DEL id={_id} [{reason}] {link}')
    if len(to_delete) > 50:
        logger.info(f'  …还有 {len(to_delete) - 50} 行（见 cleanup.log）')
    for _id, link, reason in review:
        logger.warning(f'  REVIEW id={_id} [{reason}] {link}')

    if not APPLY:
        logger.info('DRY-RUN 结束，未修改数据库。确认无误后加 --apply 执行。')
        return

    # 5. 真实删除（article_categories 有 ON DELETE CASCADE，会连带清理）
    logger.info(f'开始删除 {len(to_delete)} 行…')
    deleted = 0
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        batch = 500
        ids = [d[0] for d in to_delete]
        for i in range(0, len(ids), batch):
            chunk = ids[i:i + batch]
            placeholders = ','.join(['%s'] * len(chunk))
            cursor.execute(f'DELETE FROM articles WHERE id IN ({placeholders})', chunk)
            deleted += cursor.rowcount
            logger.info(f'  已删除 {deleted}/{len(ids)}')
    total = db_manager.get_article_count()
    logger.info('=' * 50)
    logger.info(f'清理完成：删除 {deleted} 行，数据库现有 {total} 篇文章')
    logger.info('=' * 50)


if __name__ == '__main__':
    main()
