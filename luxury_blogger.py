import os
import random
import re
import requests
import time
import base64
import json
import tempfile
from playwright.sync_api import sync_playwright

CACHE_FILE = "posted_cache.txt"


def click_physical(page, selector):
    import time
    elements = page.locator(selector).all()
    for el in elements:
        try:
            box = el.bounding_box()
            if box and box['width'] > 0 and box['height'] > 0:
                x = box['x'] + box['width'] / 2
                y = box['y'] + box['height'] / 2
                page.mouse.click(x, y)
                return True
        except:
            pass
    return False

def load_posted_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_cache(item_code):
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{item_code}\n")

def fetch_rakuten_item():
    app_id = os.environ.get("RAKUTEN_APP_ID")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY")
    if not app_id or not access_key:
        raise ValueError("RAKUTEN_APP_ID and RAKUTEN_ACCESS_KEY must be set in environment variables.")

    posted_cache = load_posted_cache()

    # 第一キーワードで検索
    keyword = "MELLOJOYスクイーズ"
    print(f"Searching Rakuten for primary keyword: {keyword}")
    item = _search_by_keyword(app_id, access_key, keyword, posted_cache)
    if item:
        return item

    # フォールバックキーワードで検索
    attributes = ["高級", "ラグジュアリー", "ハイエンド", "限定", "プレミアム", "ブランド"]
    selected_attribute = random.choice(attributes)
    keyword = f"アイテム {selected_attribute}"
    print(f"Searching Rakuten for keyword: {keyword}")

    url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "keyword": keyword,
        "format": "json",
        "hits": 30
    }
    if affiliate_id:
        params["affiliateId"] = affiliate_id

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch from Rakuten API: {response.status_code} - {response.text}")

    data = response.json()
    items = data.get("Items", [])
    if not items:
        raise RuntimeError(f"No items found for keyword: {keyword}")

    posted_cache = load_posted_cache()
    for item_wrapper in items:
        item = item_wrapper.get("Item", {})
        item_code = item.get("itemCode")
        if item_code and item_code not in posted_cache:
            return item

    raise RuntimeError("All fetched items have already been posted.")

def generate_article_with_llm(item):
    title = item.get("itemName", "")
    price = item.get("itemPrice", "")
    affiliate_id = os.environ.get("RAKUTEN_AFFILIATE_ID")
    url = get_rakuten_affiliate_url(item, affiliate_id)

    image_url = ""
    medium_images = item.get("mediumImageUrls", [])
    if medium_images:
        image_url = medium_images[0]
    else:
        small_images = item.get("smallImageUrls", [])
        if small_images:
            image_url = small_images[0]

    buy_button_html = (
        '<div style="text-align: center; margin: 20px 0;">'
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
        'style="display:inline-block; padding: 14px 28px; background-color: #bf0000; '
        'color: #ffffff; font-weight: bold; font-size: 16px; border-radius: 8px; '
        'text-decoration: none; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">'
        '\U0001F6D2 \u697d\u5929\u5e02\u5834\u3067\u4fa1\u683c\u30fb\u5728\u5eab\u3092\u898b\u308b</a></div>'
    )

    prompt = (
        "\u4ee5\u4e0b\u306e\u697d\u5929\u306e\u5546\u54c1\u60c5\u5831\u3092\u57fa\u306b\u3057\u3066\u3001"
        "\u30d6\u30ed\u30b0\u8a18\u4e8b\u306e\u30bf\u30a4\u30c8\u30eb\u3068HTML\u672c\u6587\u3092\u751f\u6210\u3057\u3066\u304f\u3060\u3055\u3044\u3002\n"
        f"\u5546\u54c1\u540d: {title}\n"
        f"\u4fa1\u683c: {price}\u5186\n"
        f"\u5546\u54c1\u753b\u50cfURL: {image_url}\n"
        f"\u30a2\u30d5\u30a3\u30ea\u30a8\u30a4\u30c8URL: {url}\n"
        "\u697d\u5929ROOM: https://room.rakuten.co.jp/jack555/items\n\n"
        "\u4ee5\u4e0b\u306e\u8981\u4ef6\u3092\u53b3\u683c\u306b\u9075\u5b88\u3057\u3066\u304f\u3060\u3055\u3044\uff1a\n"
        "1. \u51fa\u529b\u306f\u4ee5\u4e0b\u306eJSON\u30d5\u30a9\u30fc\u30de\u30c3\u30c8\u306e\u307f\u3068\u3057\u3066\u304f\u3060\u3055\u3044\u3002"
        "\u4ed6\u306e\u30c6\u30ad\u30b9\u30c8\u306f\u4e00\u5207\u542b\u3081\u306a\u3044\u3067\u304f\u3060\u3055\u3044\u3002\n"
        '{"title": "\u30ad\u30e3\u30c3\u30c1\u30fc\u306a\u30bf\u30a4\u30c8\u30eb\uff08\u6700\u592735\u6587\u5b57\uff09",'
        ' "html": "\u7d14\u7c8b\u306aHTML\u672c\u6587"}\n'
        "2. HTML\u672c\u6587\u306e\u69cb\u6210\uff1a\n"
        '   - \u8a18\u4e8b\u5168\u4f53\u3092 <div class=\"premium-squishy-article\"> \u3068 </div> \u3067\u56f2\u3080\n'
        '   - \u5546\u54c1\u306e\u9b45\u529b\u7684\u306a\u8aac\u660e\uff08<div class=\"premium-content-body\"> \u3068 </div> \u3067\u56f2\u3080\uff09\n'
        "3. \u5546\u54c1\u306e\u5177\u4f53\u7684\u306a\u9b45\u529b\u30fb\u7279\u5fb4\u3092\u76db\u308a\u8fbc\u3093\u3067\u304f\u3060\u3055\u3044\u3002\n"
        "4. \u65e5\u672c\u8a9e\u3067\u3001\u30d7\u30ec\u30df\u30a2\u30e0\u611f\u306e\u3042\u308b\u6587\u4f53\u3067\u66f8\u3044\u3066\u304f\u3060\u3055\u3044\u3002\n"
    )

    system_message = (
        "\u3042\u306a\u305f\u306f\u9ad8\u7d1a\u5546\u54c1\u5c02\u9580\u306e\u30d6\u30ed\u30b0\u30e9\u30a4\u30bf\u30fc\u3067\u3059\u3002"
        "\u6307\u5b9a\u3055\u308c\u305fJSON\u30d5\u30a9\u30fc\u30de\u30c3\u30c8\uff08title\u3068html\u306e\u307f\uff09\u3067\u51fa\u529b\u3057\u3066\u304f\u3060\u3055\u3044\u3002"
    )

    def try_parse_json(text, fallback_text):
        import json as _json
        t = text.strip()
        if t.startswith("```"):
            parts = t.split("```")
            t = parts[2] if len(parts) >= 3 else t.replace("```json", "").replace("```", "")
        t = t.strip()
        try:
            data = _json.loads(t)
            if "title" in data and "html" in data:
                return data
        except Exception:
            pass
        return {"title": "\u6ce8\u76ee" + title[:20] + "...", "html": fallback_text or t}

    # 1. Gemini API
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        for model_name in ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]:
            try:
                api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_message}\n\n{prompt}"}]}],
                    "generationConfig": {"temperature": 0.8, "maxOutputTokens": 2048}
                }
                if "2.5" in model_name:
                    payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
                res = requests.post(api_url, json=payload, timeout=45)
                if res.status_code == 200:
                    data = res.json()
                    candidate = data.get("candidates", [{}])[0]
                    parts_list = candidate.get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts_list if p.get("text")).strip()
                    if len(text) > 50:
                        print(f"Generated article via Gemini API ({model_name}).")
                        return try_parse_json(text, text)
                else:
                    print(f"Gemini API ({model_name}) returned {res.status_code}: {res.text[:100]}")
            except Exception as e:
                print(f"Gemini API ({model_name}) error: {e}")

    # 2. Groq API
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        for model_name in ["llama-3.3-70b-versatile", "llama3-70b-8192"]:
            try:
                headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                payload = {
                    "model": model_name,
                    "messages": [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 2048
                }
                res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=45)
                if res.status_code == 200:
                    text = res.json()["choices"][0]["message"]["content"].strip()
                    if len(text) > 50:
                        print(f"Generated article via Groq API ({model_name}).")
                        return try_parse_json(text, text)
                else:
                    print(f"Groq API ({model_name}) returned {res.status_code}: {res.text[:100]}")
            except Exception as e:
                print(f"Groq API ({model_name}) error: {e}")

    # 3. OpenRouter API
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        for model_name in ["google/gemma-3-27b-it:free", "mistralai/mistral-nemo:free"]:
            try:
                headers = {
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com",
                    "X-Title": "LuxuryBlogger"
                }
                payload = {
                    "model": model_name,
                    "messages": [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 2048
                }
                res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=45)
                if res.status_code == 200:
                    text = res.json()["choices"][0]["message"]["content"].strip()
                    if len(text) > 50:
                        print(f"Generated article via OpenRouter ({model_name}).")
                        return try_parse_json(text, text)
                else:
                    print(f"OpenRouter ({model_name}) returned {res.status_code}: {res.text[:100]}")
            except Exception as e:
                print(f"OpenRouter ({model_name}) error: {e}")

    # 4. GitHub Models API
    gh_token = os.environ.get("GH_TOKEN")
    if gh_token and not gh_token.startswith("ghs_"):
        try:
            headers = {"Authorization": f"Bearer {gh_token}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
                "temperature": 0.8,
                "max_tokens": 2048
            }
            res = requests.post("https://models.inference.ai.azure.com/chat/completions", headers=headers, json=payload, timeout=45)
            if res.status_code == 200:
                text = res.json()["choices"][0]["message"]["content"].strip()
                if len(text) > 50:
                    print("Generated article via GitHub Models API.")
                    return try_parse_json(text, text)
            else:
                print(f"GitHub Models API returned {res.status_code}: {res.text[:100]}")
        except Exception as e:
            print(f"GitHub Models API error: {e}")

    print("WARNING: All LLM generation attempts failed. Using local template.")
    fallback_html = (
        '<div class="premium-squishy-article">'
        f'<div class="premium-image-wrapper"><img src="{image_url}" alt="{title}" /></div>'
        '<div class="premium-content-body">'
        f'<h2 style="font-size: 20px; color: #2c2302; margin-top: 10px; margin-bottom: 15px;">{title}</h2>'
        '<p>\u3053\u3061\u3089\u306e\u5546\u54c1\u3092\u3054\u7d39\u4ecb\u3057\u307e\u3059\u3002'
        '\u30d7\u30ec\u30df\u30a2\u30e0\u306a\u54c1\u8cea\u3068\u6d17\u7df4\u3055\u308c\u305f\u30c7\u30b6\u30a4\u30f3\u304c\u9b45\u529b\u306e\u30a2\u30a4\u30c6\u30e0\u3067\u3059\u3002</p>'
        '<ul class="premium-points-list">'
        '<li><strong>\u9ad8\u54c1\u8cea\u306a\u4ed5\u69d8\uff1a</strong> '
        '\u4e0a\u8cea\u306a\u7d20\u6750\u3068\u4e01\u5be7\u306a\u4ed5\u4e0a\u304c\u308a\u304c\u5149\u308b\u4e00\u54c1\u3067\u3059\u3002</li>'
        '<li><strong>\u30c7\u30b6\u30a4\u30f3\u6027\uff1a</strong> '
        '\u30a4\u30f3\u30c6\u30ea\u30a2\u3068\u3057\u3066\u3082\u6620\u3048\u308b\u6d17\u7df4\u3055\u308c\u305f\u30c7\u30b6\u30a4\u30f3\u3002</li>'
        '<li><strong>\u30b3\u30b9\u30c8\u30d1\u30d5\u30a9\u30fc\u30de\u30f3\u30b9\uff1a</strong> '
        '\u3053\u306e\u30af\u30aa\u30ea\u30c6\u30a3\u3067\u3053\u306e\u4fa1\u683c\u306f\u898b\u9003\u305b\u307e\u305b\u3093\u3002</li>'
        '</ul>'
        f'<p style="font-size: 15px; margin-bottom: 25px;">\u73fe\u5728 <strong>{price}\u5186</strong> \u3067\u304a\u6c42\u3081\u3044\u305f\u3060\u3051\u307e\u3059\u3002</p>'
        '</div>'
        f'{buy_button_html}'
        '</div>'
    )
    return {
        "title": f"\u6ce8\u76ee\u30a2\u30a4\u30c6\u30e0 {title[:25]}...",
        "html": fallback_html
    }

def proofread_and_optimize_blogger_article(title, html_content):
    """誤字脱字最終チェックとSEO, AI-SEO, GEO的な修正ブラッシュアップ工程"""
    if not html_content or len(html_content.strip()) < 50:
        return html_content

    prompt = f"""以下のブログ記事HTMLに対して、誤字脱字チェックとSEO・AI-SEO・GEO（Generative Engine Optimization）最適化を行い、最高品質の原稿にブラッシュアップしてください。

【タイトル】: {title}
【HTML本文】:
{html_content}

【ブラッシュアップ要件】:
1. 誤字脱字・不自然な日本語表現を完全に校正してください。
2. AI検索（Perplexity, ChatGPT, Gemini等）が回答の根拠として引用しやすくするため、商品の具体的な魅力・メリット・特徴を構造化してください。
3. 文章が途中で力尽きず、タグ構造と文脈が完全に完結していることを確認してください。
4. 前置き・解説なしで修正後のHTML本文のみを出力してください。
"""

    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if github_token:
        try:
            headers = {"Authorization": f"Bearer {github_token}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "あなたはプロのWeb校正者兼SEO/GEOアナリストです。誤字脱字を無くし最高品質のHTML本文のみを出力します。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5
            }
            resp = requests.post("https://models.inference.ai.azure.com/chat/completions", headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                res_text = resp.json()["choices"][0]["message"]["content"].strip()
                if "```html" in res_text: res_text = res_text.split("```html", 1)[1].split("```")[0]
                elif "```" in res_text: res_text = res_text.split("```", 1)[1].split("```")[0]
                if len(res_text.strip()) > 100:
                    return res_text.strip()
        except Exception as e:
            print(f"Proofread failed: {e}")
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            print("Proofreading with Groq API...")
            headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "あなたはプロのWeb校正者兼SEO/GEOアナリストです。誤字脱字を無くし最高品質のHTML本文のみを出力します。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5
            }
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                res_text = resp.json()["choices"][0]["message"]["content"].strip()
                if "```html" in res_text: res_text = res_text.split("```html", 1)[1].split("```")[0]
                elif "```" in res_text: res_text = res_text.split("```", 1)[1].split("```")[0]
                if len(res_text.strip()) > 100:
                    print("Successfully proofread with Groq API!")
                    return res_text.strip()
        except Exception as e:
            print(f"Groq proofread failed: {e}")

    return html_content

def ensure_complete_blogger_article(html_content):
    """途中切れ（力尽きる現象）を検知し、安全に文末とHTML閉じタグを補正する"""
    if not html_content:
        return html_content
    html_content = html_content.strip()
    valid_endings = ("。", "！", "？", "!", "?", "</div>", "</p>", "</ul>", "</li>", "</a>")
    if not html_content.endswith(valid_endings):
        print("WARNING: Incomplete article detected. Repairing endings and tags...")
        last_p = max(html_content.rfind("。"), html_content.rfind("！"), html_content.rfind("</div>"))
        if last_p > len(html_content) * 0.5:
            html_content = html_content[:last_p + 1]

    open_divs = html_content.count("<div")
    close_divs = html_content.count("</div>")
    if open_divs > close_divs:
        html_content += "</div>" * (open_divs - close_divs)
    return html_content

def post_to_blogger(title, content):
    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    if not blog_id:
        raise ValueError("BLOGGER_BLOG_ID is not set in environment variables.")
    session_b64 = os.environ.get("BLOGGER_SESSION_B64")
    
    session_file_path = None
    if session_b64:
        try:
            decoded_str = base64.b64decode(session_b64).decode('utf-8')
            json.loads(decoded_str)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".json") as temp_file:
                temp_file.write(decoded_str)
                session_file_path = temp_file.name
        except Exception as e:
            raise ValueError(f"BLOGGER_SESSION_B64 のデコードに失敗しました: {e}")
    elif os.path.exists("session.json"):
        print("Found local session.json. Using it for Blog Post.")
        session_file_path = "session.json"
    else:
        raise ValueError(f"BLOGGER_SESSION_B64 is not set and local session.json not found.")

    print(f"Posting to Blogger (Blog ID: {blog_id}) using Playwright...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                storage_state=session_file_path,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                permissions=['clipboard-read', 'clipboard-write']
            )
            
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            try:
                time.sleep(random.uniform(3.0, 5.0))

                page.goto(f"https://draft.blogger.com/blog/post/edit/{blog_id}/new", wait_until="networkidle")
                time.sleep(random.uniform(3.0, 5.0))
                
                # もし画面が遷移していなかったら、キーボードショートカット 'c' (新規投稿) を試す
                if "edit" not in page.url:
                    page.keyboard.press('c')
                    time.sleep(random.uniform(3.0, 5.0))
                
                # それでもダメならJSで強制的に「新しい投稿」ボタンをクリックする
                if "edit" not in page.url:
                    page.evaluate('''() => {
                        const btns = Array.from(document.querySelectorAll('div[role="button"]'));
                        const newPostBtn = btns.find(b => (b.getAttribute('aria-label') || '').includes('新しい投稿') || (b.getAttribute('aria-label') || '').includes('New post'));
                        if (newPostBtn) newPostBtn.click();
                    }''')
                    time.sleep(random.uniform(3.0, 5.0))

                # 1. タイトル入力
                title_input = page.locator('.titleField input, input[aria-label*="Title"], input[aria-label*="タイトル"]').first
                title_input.wait_for(state="visible", timeout=30000)
                title_input.click()
                time.sleep(0.5)
                # タイトルを全消去して入力
                page.keyboard.press('Meta+A')
                page.keyboard.press('Control+A')
                page.keyboard.press('Backspace')
                # 1-2. タイトルと本文入力（検証ループ付き）
                max_retries = 3
                success = False
                
                for attempt in range(max_retries):
                    print(f"--- Attempt {attempt+1} / {max_retries} ---")
                    
                    if attempt > 0:
                        print("Reloading page for retry...")
                        page.reload(wait_until="domcontentloaded")
                        time.sleep(3)
                    
                    try:
                        title_input = page.locator('input.titleField, input[aria-label="タイトル"], input[aria-label="Title"]').locator("visible=true").first
                        title_input.fill(title)
                        time.sleep(2)
                        
                        print("Focusing on the rich text editor via Tab navigation...")
                        # タイトル入力後、Tabキーを2回押せば通常本文エリアにフォーカスが当たる
                        page.keyboard.press('Tab')
                        time.sleep(0.5)
                        page.keyboard.press('Tab')
                        time.sleep(1)
                        
                        # 念のためエディタらしきものをクリックも試す
                        try:
                            editor_body = page.locator('div[aria-label="本文"], div[aria-label="Body"], div[role="textbox"], iframe').locator("visible=true").first
                            editor_body.click(timeout=3000)
                        except:
                            pass
                            
                        print("Injecting HTML via Playwright clipboard paste...")
                        # クリップボードにHTMLとしてコピー
                        page.evaluate('''html => {
                            try {
                                const blob = new Blob([html], { type: 'text/html' });
                                const data = [new ClipboardItem({ 'text/html': blob })];
                                navigator.clipboard.write(data);
                            } catch (e) {
                                console.error('Clipboard write failed:', e);
                            }
                        }''', content)
                        time.sleep(2)
                        
                        # ペースト実行
                        page.keyboard.press('Control+V')
                        page.keyboard.press('Meta+V') # Mac用
                        time.sleep(2)
                        
                        # Wizオートセーブ誘発のためのダミータイピング
                        print("Triggering Wiz autosave...")
                        page.keyboard.press('Space')
                        time.sleep(0.5)
                        page.keyboard.press('Backspace')
                        time.sleep(3)
                        
                        # --- 本文入力の検証 ---
                        print("Validating injected content...")
                        # 特定の要素にこだわらず、ページ全体のHTMLを取得して画像タグが含まれるか確認する
                        page_html = page.content()
                        
                        if "<img" in page_html and ("href" in page_html or "http" in page_html):
                            print("Validation passed: Body content (image and links) successfully detected in page!")
                            success = True
                            break
                        else:
                            print("Validation failed: Body seems empty or missing images in page DOM.")
                            print("Page HTML snippet:", page_html[:200])
                            
                    except Exception as e:
                        print(f"Error during injection attempt {attempt+1}: {e}")
                        
                    time.sleep(3)
                
                if not success:
                    raise Exception("Critical Failure: Could not inject body content after 3 attempts. Aborting save to prevent empty drafts.")

                # 3. 公開ボタンのクリック
                print("Publishing post...")
                try:
                    pub_btn = page.locator('[aria-label="公開"], [aria-label="Publish"]').locator("visible=true").first
                    pub_btn.scroll_into_view_if_needed()
                    time.sleep(1)
                    pub_btn.click(force=True, timeout=10000)
                    print("Clicked publish button.")
                except Exception as e:
                    print("Failed to click publish button:", e)
                    # ショートカットフォールバック
                    page.keyboard.press('Control+Shift+P')
                    page.keyboard.press('Meta+Shift+P')
                
                time.sleep(4)

                # 4. 確認ダイアログの「確認」ボタン
                try:
                    conf_btn = page.locator('[aria-label="確認"], [aria-label="Confirm"], div[role="button"]:has-text("確認")').locator("visible=true").first
                    conf_btn.scroll_into_view_if_needed()
                    time.sleep(1)
                    conf_btn.click(force=True, timeout=10000)
                    print("Clicked confirm button.")
                except Exception as e:
                    print("Failed to click confirm button:", e)
                    page.keyboard.press('Enter')
                
                # 公開通信完了まで十分待機
                time.sleep(10)
                print("Successfully published post using Playwright!")
            except Exception as e:
                print(f"Error occurred. Current URL: {page.url}")
                print(f"Page Title: {page.title()}")
                print(f"Page Content Snippet: {page.content()[:1000]}")
                raise e

    finally:
        if os.path.exists(session_file_path):
            os.remove(session_file_path)


def generate_room_comment_with_llm(item):
    import random
    title = item.get("itemName") or item.get("title") or ""
    price = item.get("itemPrice") or item.get("price") or ""
    caption = item.get("itemCaption") or item.get("catchcopy") or ""

    prompt = f"""以下の楽天の商品情報を基にして、楽天ROOM用の紹介コメント（400文字以内）を生成してください。
【商品名】: {title}
【価格】: {price}円
【商品説明・特徴】: {caption[:200]}

以下の要件を厳格に遵守してください：
1. 口調・トーン：「これ気になってた！」「これかわいい！」「これ便利だよ！」といった親しみやすく共感できる会話調にすること。
2. 文字数：400文字以内（厳守。超えると投稿エラーになります）。
3. 絵文字：5〜8個使用して華やかにすること。
4. ハッシュタグ：3〜5個（商品のカテゴリや関連するもの）含め、末尾に「#楽天市場」を必ず含めること。
5. URLや疑似リンク、プレースホルダー（「[リンクはこちら]」など）は絶対に含めないでください。
6. 出力は紹介コメントのテキストのみとし、前置きやMarkdownの装飾コードブロック等は一切含めないでください。
"""

    system_message = (
        "あなたは楽天ROOMでフォロワー急増中の人気インフルエンサーです。"
        "「これ気になってた！」「これかわいい！」「これ便利だよ！」などの親しみやすい口調で、"
        "商品の魅力を共感たっぷりに伝えてください。"
    )

    def clean_text(text):
        return text.replace("```", "").strip()

    # 1. Gemini API（最優先。thinking無効化・全parts結合で安定化）
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        for model_name in ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_message}\n\n{prompt}"}]}],
                    "generationConfig": {"temperature": 0.9, "maxOutputTokens": 600}
                }
                if "2.5" in model_name:
                    payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
                res = requests.post(url, json=payload, timeout=30)
                if res.status_code == 200:
                    data = res.json()
                    candidate = data.get("candidates", [{}])[0]
                    parts = candidate.get("content", {}).get("parts", [])
                    text = clean_text("".join(p.get("text", "") for p in parts if p.get("text")))
                    if len(text) > 30:
                        print(f"Successfully generated ROOM comment via Gemini API ({model_name}).")
                        return text
                    finish = candidate.get("finishReason", "UNKNOWN")
                    print(f"Gemini ({model_name}) short/empty. finishReason={finish}, text_len={len(text)}")
                else:
                    print(f"Gemini API ({model_name}) returned {res.status_code}: {res.text[:150]}")
            except Exception as e:
                print(f"Gemini API ({model_name}) error: {e}")

    # 2. Groq API
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        for model_name in ["llama-3.3-70b-versatile", "llama3-70b-8192", "llama3-8b-8192"]:
            try:
                headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                payload = {
                    "model": model_name,
                    "messages": [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 600
                }
                res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=25)
                if res.status_code == 200:
                    text = clean_text(res.json()["choices"][0]["message"]["content"])
                    if len(text) > 30:
                        print(f"Successfully generated ROOM comment via Groq API ({model_name}).")
                        return text
                else:
                    print(f"Groq API ({model_name}) returned {res.status_code}: {res.text[:100]}")
            except Exception as e:
                print(f"Groq API ({model_name}) error: {e}")

    # 3. OpenRouter API（有効な無料モデルを使用）
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        for model_name in ["google/gemma-3-27b-it:free", "mistralai/mistral-nemo:free", "meta-llama/llama-3.2-3b-instruct:free"]:
            try:
                headers = {
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com",
                    "X-Title": "RakutenRoomBot"
                }
                payload = {
                    "model": model_name,
                    "messages": [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 600
                }
                res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if res.status_code == 200:
                    text = clean_text(res.json()["choices"][0]["message"]["content"])
                    if len(text) > 30:
                        print(f"Successfully generated ROOM comment via OpenRouter ({model_name}).")
                        return text
                else:
                    print(f"OpenRouter ({model_name}) returned {res.status_code}: {res.text[:100]}")
            except Exception as e:
                print(f"OpenRouter ({model_name}) error: {e}")

    # 4. GitHub Models API（GH_TOKENがPATの場合のみ）
    gh_token = os.environ.get("GH_TOKEN")
    if gh_token and not gh_token.startswith("ghs_"):
        for model_name in ["gpt-4o-mini", "gpt-4o", "Meta-Llama-3.1-8B-Instruct"]:
            try:
                headers = {"Authorization": f"Bearer {gh_token}", "Content-Type": "application/json"}
                payload = {
                    "model": model_name,
                    "messages": [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 600
                }
                res = requests.post("https://models.inference.ai.azure.com/chat/completions", headers=headers, json=payload, timeout=25)
                if res.status_code == 200:
                    text = clean_text(res.json()["choices"][0]["message"]["content"])
                    if len(text) > 30:
                        print(f"Successfully generated ROOM comment via GitHub Models API ({model_name}).")
                        return text
                else:
                    print(f"GitHub Models API ({model_name}) returned {res.status_code}: {res.text[:100]}")
            except Exception as e:
                print(f"GitHub Models API ({model_name}) error: {e}")

    print("WARNING: All LLM API calls failed. Generating dynamic item-aware comment.")
    clean_title = title.replace("【", "").replace("】", "").replace("！", "").replace("✨", "")[:45]
    words = [w for w in clean_title.split() if len(w) > 1]
    keyword = words[0] if words else "おすすめ"

    starters = [
        f"これ気になってた！「{clean_title}」すごく良さそうで目をつけてました✨",
        f"これかわいい！「{clean_title}」のデザインに一目惚れしちゃった💕",
        f"これ便利だよ！「{clean_title}」は持っておくと日常で大活躍しそう👍",
        f"これ気になってた！話題の「{clean_title}」を見つけて即チェック🎁",
        f"これ便利だよ！生活のクオリティが上がりそうな「{clean_title}」✨"
    ]
    starter = random.choice(starters)

    bodies = [
        "実用性抜群で見た目のセンスも最高のアイテム！自分用はもちろんギフトにもぴったりだね😊",
        "使ってみた人の評価も高くて期待大！毎日の生活がもっと楽しくなりそう✨",
        "細部までこだわりを感じる優秀アイテム。気になる人はぜひチェックしてみてね🛍️",
        "このクオリティでこの価格は本当に魅力的！見つけたら早めのチェックがおすすめ👍"
    ]
    body = random.choice(bodies)

    price_info = f"（価格: {price}円）" if price else ""
    return f"{starter}\n\n{body}\n{price_info}\n\n#{keyword} #楽天市場 #おすすめアイテム #コレ"



def post_to_rakuten_room(item_code, comment):
    session_b64 = os.environ.get("ROOM_SESSION_B64") or os.environ.get("BLOGGER_SESSION_B64")
    
    session_file_path = None
    if session_b64:
        try:
            decoded_str = base64.b64decode(session_b64).decode('utf-8')
            json.loads(decoded_str)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".json") as temp_file:
                temp_file.write(decoded_str)
                session_file_path = temp_file.name
        except Exception as e:
            print(f"ROOM_SESSION_B64 (or BLOGGER_SESSION_B64) decode failed: {e}")
            return
    elif os.path.exists("session.json"):
        print("Found local session.json. Using it for Rakuten Room.")
        session_file_path = "session.json"
    else:
        print("ROOM_SESSION_B64/BLOGGER_SESSION_B64 is not set and local session.json not found. Skipping Rakuten Room post.")
        return

    print(f"Posting to Rakuten Room (Item: {item_code}) using Playwright...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                storage_state=session_file_path,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            try:
                # ROOM投稿エディタへ遷移
                warp_url = f"https://room.rakuten.co.jp/mix?itemcode={item_code}&scid=we_room_upc60"
                page.goto(warp_url, wait_until="load", timeout=45000)
                time.sleep(4)

                # ログイン画面に飛ばされていないかチェック
                if "login.rakuten.co.jp" in page.url or "login" in page.url.lower():
                    print("Error: Session has expired or is invalid. Redirected to Rakuten login page. Skipping Rakuten Room post.")
                    return

                # 重複・すでにコレしているかチェック
                page_html = page.content()
                if any(term in page_html for term in ["すでにコレ", "すでに登録されています", "すでに登録"]):
                    print("This item has already been posted ('コレ！'済み) to Rakuten Room. Skipping.")
                    return

                # コメント入力欄 (textarea)
                comment_area = page.locator('textarea[placeholder*="コメント"], textarea[placeholder*="オススメ"], textarea[placeholder*="魅力"], textarea').first
                comment_area.wait_for(state="visible", timeout=15000)
                comment_area.fill(comment)
                time.sleep(1)

                # 投稿確定ボタン
                submit_btn = page.locator('button:has-text("投稿"), button:has-text("完了"), button:has-text("コレ！"), button[class*="submit"]').first
                submit_btn.scroll_into_view_if_needed()
                time.sleep(1)
                submit_btn.click(force=True)
                print("Clicked Rakuten Room submit button.")
                
                time.sleep(5)
                print("Successfully posted to Rakuten Room!")
            except Exception as inner_e:
                print(f"Error during Playwright interaction: {inner_e}")
                try:
                    page.screenshot(path="room_error.png")
                    print("Saved debug screenshot: room_error.png")
                except Exception as se:
                    print(f"Failed to take screenshot: {se}")
                raise inner_e

    except Exception as e:
        print(f"Error posting to Rakuten Room: {e}")
    finally:
        if session_file_path and session_file_path != "session.json" and os.path.exists(session_file_path):
            os.remove(session_file_path)


def main():
    try:
        # 1. 楽天から商品取得
        item = fetch_rakuten_item()
        item_code = item.get("itemCode")
        title = item.get("itemName")
        print(f"Selected Item: {title} ({item_code})")

        # 2. LLMで記事生成
        llm_result = generate_article_with_llm(item)
        if isinstance(llm_result, dict):
            gen_title = llm_result.get("title", title[:30])
            html_content = llm_result.get("html", "")
        else:
            gen_title = title[:30]
            html_content = str(llm_result)
            
        if not html_content or len(html_content) < 10:
            # AIが失敗した時の絶対的なフォールバックHTML
            image_url = item.get("mediumImageUrls", [{"imageUrl": ""}])[0].get("imageUrl", "") if item.get("mediumImageUrls") else ""
            html_content = f'<h2>{gen_title}</h2><br><br><img src="{image_url}" alt="商品画像" style="max-width: 100%; height: auto;"><br><br><a href="https://room.rakuten.co.jp/jack555/items" target="_blank">✅ 私の楽天ROOMはこちら</a>'

        # 誤字脱字最終チェックとSEO, AI-SEO, GEO的な修正ブラッシュアップ工程
        html_content = proofread_and_optimize_blogger_article(gen_title, html_content)
        # 途中切れ（力尽きる現象）防止・補正工程
        html_content = ensure_complete_blogger_article(html_content)
            
        print("--- Generated HTML Content Snippet ---")
        print(html_content[:200])
        print("--------------------------------------")
        
        post_to_blogger(gen_title, html_content)

        # 楽天ROOMへも自動「コレ！」投稿
        try:
            room_comment = generate_room_comment_with_llm(item)
            print("Generated ROOM Comment:")
            print(room_comment)
            post_to_rakuten_room(item_code, room_comment)
        except Exception as room_err:
            print(f"Failed to post to Rakuten Room: {room_err}")

        # 4. キャッシュに保存
        save_to_cache(item_code)
        print("Process completed successfully.")

    except Exception as e:
        print(f"Error in execution: {e}")
        exit(1)

if __name__ == "__main__":
    main()
