import asyncio
import glob
import csv
import os
from typing import Set
from contextvars import ContextVar

import config
from playwright.async_api import async_playwright
from media_platform.weibo.core import WeiboCrawler
from media_platform.weibo.login import WeiboLogin
from media_platform.weibo.exception import DataFetchError
from tools import utils
from store.weibo import WeiboCsvStoreImplement
from var import crawler_type_var


def collect_unique_user_ids() -> Set[str]:
    """Collect unique user IDs from all search_contents CSV files."""
    user_ids = set()
    csv_dir = os.path.join("data", "weibo", "csv")
    for path in glob.glob(os.path.join(csv_dir, "search_contents_*.csv")):
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row.get('user_id')
                if uid and uid.strip():
                    user_ids.add(uid.strip())
    return user_ids


def load_already_fetched_users() -> Set[str]:
    """Load user_ids that have already been fetched from poster_info CSV files."""
    fetched_ids = set()
    csv_dir = os.path.join("data", "weibo", "csv")
    for path in glob.glob(os.path.join(csv_dir, "search_poster_info_*.csv")):
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    uid = row.get('user_id')
                    if uid and uid.strip():
                        fetched_ids.add(uid.strip())
        except Exception as e:
            utils.logger.warning(f"Failed to read {path}: {e}")
    return fetched_ids


async def fetch_and_save_creator_info() -> None:
    """
    Fetch creator info for each unique user_id using WeiboCrawler workflow.
    Reuses login session and WeiboClient to avoid API verification issues.
    """
    # Set crawler_type for proper file naming
    crawler_type_var.set("search")
    
    user_ids = collect_unique_user_ids()
    if not user_ids:
        utils.logger.info("No user_id found in data/weibo/csv/search_contents_*.csv")
        return
    
    # Remove already fetched users to avoid duplicates
    already_fetched = load_already_fetched_users()
    remaining_user_ids = user_ids - already_fetched
    
    utils.logger.info(f"[fetch_poster_info] Found {len(user_ids)} unique users, {len(already_fetched)} already fetched, {len(remaining_user_ids)} to fetch")
    
    if not remaining_user_ids:
        utils.logger.info("[fetch_poster_info] All users already fetched!")
        return
    
    # Initialize CSV store
    csv_store = WeiboCsvStoreImplement()

    crawler = WeiboCrawler()
    async with async_playwright() as playwright:
        # Launch browser (same as WeiboCrawler.start)
        utils.logger.info("[fetch_poster_info] Launching browser...")
        if config.ENABLE_CDP_MODE:
            utils.logger.info("[fetch_poster_info] Using CDP mode")
            browser_context = await crawler.launch_browser_with_cdp(playwright, None, crawler.mobile_user_agent, headless=config.CDP_HEADLESS)
        else:
            utils.logger.info("[fetch_poster_info] Using standard mode")
            browser_context = await crawler.launch_browser(playwright.chromium, None, crawler.mobile_user_agent, headless=config.HEADLESS)
        crawler.browser_context = browser_context
        crawler.context_page = await crawler.browser_context.new_page()
        
        # Go to PC index and add stealth script
        await crawler.context_page.goto(crawler.index_url)
        await asyncio.sleep(2)
        try:
            await crawler.browser_context.add_init_script(path="libs/stealth.min.js")
        except Exception:
            pass

        # Create WeiboClinient for API calls
        wb_client = await crawler.create_weibo_client(httpx_proxy=None)
        
        # Check login state and handle login if needed
        if not await wb_client.pong():
            utils.logger.info("[fetch_poster_info] Need to login, starting WeiboLogin...")
            login_obj = WeiboLogin(
                login_type=config.LOGIN_TYPE,
                login_phone="",
                browser_context=crawler.browser_context,
                context_page=crawler.context_page,
                cookie_str=config.COOKIES,
            )
            await login_obj.begin()
            utils.logger.info("[fetch_poster_info] Login finished, redirecting to mobile and updating cookies...")
            await crawler.context_page.goto(crawler.mobile_index_url)
            await asyncio.sleep(3)
            await wb_client.update_cookies(
                browser_context=crawler.browser_context,
                urls=[crawler.mobile_index_url]
            )
        else:
            utils.logger.info("[fetch_poster_info] Already logged in, skipping login")
            # Make sure we're on mobile version with updated cookies
            await crawler.context_page.goto(crawler.mobile_index_url)
            await asyncio.sleep(2)
        
        # Fetch creator info for each user ID (sequential to avoid throttling)
        success_count = 0
        failed_count = 0
        for idx, user_id in enumerate(remaining_user_ids, 1):
            try:
                utils.logger.info(f"[fetch_poster_info] ({idx}/{len(remaining_user_ids)}) Fetching creator {user_id}...")
                creator_info_res = await wb_client.get_creator_info_by_id(creator_id=user_id)
                if creator_info_res:
                    creator_info = creator_info_res.get("userInfo", {})
                    if creator_info:
                        # Convert raw API data to standardized format
                        save_item = {
                            'user_id': user_id,
                            'nickname': creator_info.get('screen_name', ''),
                            'gender': creator_info.get('gender', ''),
                            'avatar': creator_info.get('avatar_hd', ''),
                            'desc': creator_info.get('description', ''),
                            'follows': str(creator_info.get('follow_count', '0')),
                            'fans': creator_info.get('followers_count_str', ''),
                            'tag_list': '',
                            'last_modify_ts': str(utils.get_current_timestamp())
                        }
                        await csv_store.writer.write_to_csv(item_type='creators', item=save_item)
                        utils.logger.info(f"[fetch_poster_info] ✓ Saved creator {user_id}: {save_item['nickname']}")
                        success_count += 1
                    else:
                        utils.logger.warning(f"[fetch_poster_info] Empty userInfo for {user_id}")
                        failed_count += 1 
                else:
                    utils.logger.warning(f"[fetch_poster_info] No response for {user_id}")
                    failed_count += 1
                
                # Delay between requests to avoid throttling
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                
            except DataFetchError as e:
                utils.logger.error(f"[fetch_poster_info] DataFetchError for {user_id}: {e}")
                failed_count += 1
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
            except Exception as e:
                utils.logger.error(f"[fetch_poster_info] Unexpected error for {user_id}: {e}")
                failed_count += 1
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
        
        utils.logger.info(f"[fetch_poster_info] Done! Success: {success_count}, Failed: {failed_count}")


if __name__ == '__main__':
    asyncio.run(fetch_and_save_creator_info())



