# -*- coding: utf-8 -*-
"""爬取微博热搜关键词，
后续通过关键词方法爬取相关内容"""
import asyncio
from typing import List
from playwright.async_api import async_playwright
from tools import utils
import os
from datetime import datetime

PROJECT_PATH = os.path.dirname(os.getcwd())

class WeiboHotSearchCrawler:
    def __init__(self):
        self.hot_search_url = "https://s.weibo.com/top/summary"
        self.hot_words_dir = os.path.join(PROJECT_PATH, "data", "words", "hot_words")
        os.makedirs(self.hot_words_dir, exist_ok=True)

    async def get_hot_keywords(self) -> List[str]:
        """获取热搜关键词"""
        keywords = []
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=utils.get_user_agent()
                )
                page = await context.new_page()
                
                utils.logger.info("[WeiboHotSearchCrawler] Accessing hot search page...")
                await page.goto(self.hot_search_url)
                await asyncio.sleep(3)  # 等待页面加载
                
                # 解析热搜关键词 - 需要根据实际页面结构调整选择器
                keyword_elements = await page.query_selector_all("td.td-02 a")
                
                for element in keyword_elements[:50]:  # 限制前50个
                    text = await element.inner_text()
                    if text and text.strip():
                        keywords.append(text.strip())
                
                await browser.close()
                
        except Exception as e:
            utils.logger.error(f"[WeiboHotSearchCrawler] Error getting hot keywords: {e}")
        
        return keywords

async def main():
    crawler = WeiboHotSearchCrawler()
    hot_keywords = await crawler.get_hot_keywords()
    if not hot_keywords:
        print("未获取到热搜关键词")
        return

    print("微博热搜关键词：")
    for idx, kw in enumerate(hot_keywords, 1):
        print(f"{idx}. {kw}")
    
    # 保存到带日期的文件
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"hot_keywords_{timestamp}.txt"
    out_path = os.path.join(crawler.hot_words_dir, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(hot_keywords))
    print(f"已保存：{out_path}")

if __name__ == "__main__":
    asyncio.run(main())