#!/usr/bin/env python3
"""
scripts/generate_report.py
Generate HTML and Markdown reports from scraped data
"""

import json
from datetime import datetime
from pathlib import Path
from jinja2 import Template

REPORTS_DIR = Path('reports')
OUTPUT_DIR = Path('output')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Threads Crawl Report - {{ date }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 2em; font-weight: bold; color: #667eea; }
        .stat-label { color: #666; margin-top: 5px; }
        .posts { background: white; border-radius: 8px; padding: 20px; }
        .post { border-bottom: 1px solid #eee; padding: 15px 0; }
        .post:last-child { border-bottom: none; }
        .status-success { color: #10b981; }
        .status-error { color: #ef4444; }
        .timestamp { color: #888; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Threads Crawl Report</h1>
        <p class="timestamp">Generated: {{ scraped_at }}</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-value {% if status == 'success' %}status-success{% else %}status-error{% endif %}">
                {{ status | upper }}
            </div>
            <div class="stat-label">Status</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ posts_count }}</div>
            <div class="stat-label">Posts Captured</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ (html_length / 1024) | round(1) }}KB</div>
            <div class="stat-label">Page Size</div>
        </div>
    </div>
    
    <div class="posts">
        <h2>📝 Captured Content</h2>
        {% for post in posts[:20] %}
        <div class="post">{{ post[:300] }}{% if post|length > 300 %}...{% endif %}</div>
        {% endfor %}
        {% if posts|length > 20 %}
        <p style="color: #888; text-align: center;">... and {{ posts|length - 20 }} more posts</p>
        {% endif %}
    </div>
</body>
</html>
"""

MARKDOWN_TEMPLATE = """# Threads Crawl Report

**Date:** {{ date }}  
**URL:** {{ url }}  
**Status:** {{ status }}

## Summary

| Metric | Value |
|--------|-------|
| Posts Captured | {{ posts_count }} |
| Page Size | {{ (html_length / 1024) | round(1) }} KB |
| Scraped At | {{ scraped_at }} |

## Sample Content

{% for post in posts[:10] %}
### Post {{ loop.index }}
{{ post[:200] }}{% if post|length > 200 %}...{% endif %}

{% endfor %}

---
*Report generated automatically by GitHub Actions*
"""

def generate_reports():
    """Generate HTML and Markdown reports from latest scrape data"""
    REPORTS_DIR.mkdir(exist_ok=True)
    
    # Load latest data
    latest_file = OUTPUT_DIR / 'latest.json'
    if not latest_file.exists():
        print("No data file found")
        return
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Add computed fields
    data['date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    data.setdefault('posts', [])
    data.setdefault('posts_count', 0)
    data.setdefault('html_length', 0)
    data.setdefault('status', 'unknown')
    
    # Generate HTML
    html_template = Template(HTML_TEMPLATE)
    html_content = html_template.render(**data)
    
    html_file = REPORTS_DIR / 'index.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✓ Generated: {html_file}")
    
    # Generate Markdown
    md_template = Template(MARKDOWN_TEMPLATE)
    md_content = md_template.render(**data)
    
    md_file = REPORTS_DIR / 'report.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"✓ Generated: {md_file}")

if __name__ == '__main__':
    generate_reports()