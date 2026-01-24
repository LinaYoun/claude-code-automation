#!/usr/bin/env python3
"""
scripts/threads_scraper.py
Playwright-based scraper for Threads.com with CI optimization
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Configuration
CONFIG = {
    'url': os.getenv('TARGET_URL', 'https://www.threads.com/?hl=ko'),
    'timeout': 60000,
    'viewport': {'width': 1920, 'height': 1080},
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'max_scrolls': 5,
    'scroll_pause_ms': 2000,
    'output_dir': Path('output'),
    'screenshot_dir': Path('screenshots'),
}

async def create_browser_context(playwright):
    """Create browser with CI-optimized settings"""
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu',
            '--single-process',
        ]
    )
    
    context = await browser.new_context(
        viewport=CONFIG['viewport'],
        user_agent=CONFIG['user_agent'],
        locale='ko-KR',
        timezone_id='Asia/Seoul',
    )
    
    return browser, context

async def handle_popups(page):
    """Dismiss login prompts and cookie banners"""
    popup_selectors = [
        'button[aria-label="Close"]',
        '[data-testid="close-button"]',
        'button:has-text("Not now")',
        'button:has-text("Accept")',
        'button:has-text("확인")',
        '[role="dialog"] button',
    ]
    
    for selector in popup_selectors:
        try:
            element = page.locator(selector).first
            if await element.is_visible(timeout=1000):
                await element.click()
                await page.wait_for_timeout(500)
        except:
            pass

async def scroll_for_content(page, max_scrolls: int, pause_ms: int):
    """Handle infinite scroll to load dynamic content"""
    prev_height = -1
    
    for i in range(max_scrolls):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(pause_ms)
        
        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == prev_height:
            print(f"✓ Content loaded after {i + 1} scrolls")
            break
        
        prev_height = new_height
        print(f"Scrolling... {i + 1}/{max_scrolls}")

async def extract_content(page) -> dict:
    """Extract page content and metadata"""
    # Get page metadata
    title = await page.title()
    url = page.url
    
    # Extract text content
    content = await page.evaluate("""
        () => {
            const posts = [];
            document.querySelectorAll('[data-pressable-container]').forEach(el => {
                const text = el.innerText?.trim();
                if (text && text.length > 10) {
                    posts.push(text.substring(0, 500));
                }
            });
            return posts.slice(0, 50);  // Limit to 50 posts
        }
    """)
    
    # Get full HTML for archival
    html = await page.content()
    
    return {
        'url': url,
        'title': title,
        'scraped_at': datetime.now(timezone.utc).isoformat(),
        'posts_count': len(content),
        'posts': content,
        'html_length': len(html),
    }

async def main():
    """Main scraping function"""
    CONFIG['output_dir'].mkdir(exist_ok=True)
    CONFIG['screenshot_dir'].mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    async with async_playwright() as playwright:
        browser, context = await create_browser_context(playwright)
        page = await context.new_page()
        
        print(f"Navigating to: {CONFIG['url']}")
        
        try:
            # Navigate with timeout
            await page.goto(
                CONFIG['url'],
                wait_until='domcontentloaded',
                timeout=CONFIG['timeout']
            )
            
            # Handle popups
            await handle_popups(page)
            
            # Wait for dynamic content
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
            except PlaywrightTimeout:
                print("Network idle timeout - continuing with available content")
            
            # Screenshot before scroll
            await page.screenshot(
                path=CONFIG['screenshot_dir'] / f'before_scroll_{timestamp}.png',
                full_page=False
            )
            
            # Scroll to load more content
            await scroll_for_content(
                page, 
                CONFIG['max_scrolls'], 
                CONFIG['scroll_pause_ms']
            )
            
            # Screenshot after scroll
            await page.screenshot(
                path=CONFIG['screenshot_dir'] / f'after_scroll_{timestamp}.png',
                full_page=True
            )
            
            # Extract content
            data = await extract_content(page)
            data['status'] = 'success'
            
            print(f"✓ Extracted {data['posts_count']} posts")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            data = {
                'url': CONFIG['url'],
                'scraped_at': datetime.now(timezone.utc).isoformat(),
                'status': 'error',
                'error': str(e),
            }
            
            # Screenshot error state
            try:
                await page.screenshot(
                    path=CONFIG['screenshot_dir'] / f'error_{timestamp}.png'
                )
            except:
                pass
        
        finally:
            await browser.close()
    
    # Save results
    output_file = CONFIG['output_dir'] / f'threads_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Save latest symlink for easy access
    latest_file = CONFIG['output_dir'] / 'latest.json'
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Results saved to: {output_file}")
    return data

if __name__ == '__main__':
    result = asyncio.run(main())
    exit(0 if result.get('status') == 'success' else 1)