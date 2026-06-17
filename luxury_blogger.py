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
    keyword = "MELLOJOY スクイーズ"
    print(f"Searching Rakuten for primary keyword: {keyword}")
    item = _search_by_keyword(app_id, access_key, keyword, posted_cache)
    if item:
        return item

    # フォールバックキーワードで検索
    fallback_keyword = "高級スクイーズ"
    print(f"Primary keyword items all posted or empty. Searching Rakuten for fallback keyword: {fallback_keyword}")
    item = _search_by_keyword(app_id, access_key, fallback_keyword, posted_cache)
    if item:
        return item

    raise RuntimeError("All fetched items for both primary and fallback keywords have already been posted.")

def _search_by_keyword(app_id, access_key, keyword, posted_cache):
    url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "keyword": keyword,
        "format": "json",
        "hits": 30
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"Rakuten API returned error {response.status_code} for keyword '{keyword}'")
            return None
        
        data = response.json()
        items = data.get("Items", [])
        if not items:
            print(f"No items found for keyword: {keyword}")
            return None

        for item_wrapper in items:
            item = item_wrapper.get("Item", {})
            item_code = item.get("itemCode")
            if item_code and item_code not in posted_cache:
                return item
    except Exception as e:
        print(f"Error searching for keyword '{keyword}': {e}")
        return None

    return None

def generate_article_with_llm(item):
    title = item.get("itemName")
    price = item.get("itemPrice")
    url = item.get("affiliateUrl") or item.get("itemUrl")
    
    image_url = ""
    medium_images = item.get("mediumImageUrls", [])
    if medium_images:
        img_obj = medium_images[0]
        image_url = img_obj.get("imageUrl", "") if isinstance(img_obj, dict) else img_obj
    else:
        small_images = item.get("smallImageUrls", [])
        if small_images:
            img_obj = small_images[0]
            image_url = img_obj.get("imageUrl", "") if isinstance(img_obj, dict) else img_obj

    if image_url:    prompt = f"""以下の楽天の商品情報を基にして、自動投稿用のHTML記事を生成してください。
【商品名】: {title}
【価格】: {price}円
【商品画像URL】: {image_url}
【アフィリエイトURL】: {url}

以下の要件を厳格に遵守してください：
1. 出力はブログの本文となるHTMLコードのみとし、余計な説明、挨拶、前置きや後書き（例：「以下が記事です」「```html」のようなマークダウンブロック）は絶対に含めず、純粋なHTML文字列のみを出力してください。
2. 日本語のみで出力してください。
3. 画像サイズが小さくても美しく額縁のようにおしゃれに見せるため、アイキャッチ画像として、商品画像URL（{image_url}）を直接<img>タグに指定し、必ず `<div class="premium-image-wrapper">` と `</div>` で囲んで最上部に配置してください。
4. 記事構成：
   - 記事全体を `<div class="premium-squishy-article">` と `</div>` で囲んでください。
   - タイトル（<h2> または <h3> タグを使用）
   - 商品の魅力的な説明（`<div class="premium-content-body">` と `</div>` で囲むこと）：
     * コンセプト「贅沢スクイーズLife 〜SNSで話題の高級インポート＆レア触感カタログ〜」に完全に合致した内容にしてください。
     * 特に「Mellojoy」のスクイーズやレア感の高い高級スクイーズにフォーカスし、その極上の触感（もちもち、ふわふわ、低反発など）、SNSでの話題性、インポート品ならではの贅沢感と所有欲を満たす上品でプレミアムな魅力を伝える日本語の紹介文にしてください。
     * 毎回完全に独立したユニークな内容とし、他の記事と似たような言い回しやテンプレート的な文章構成の使い回しは絶対に禁止します。
   - 極上の贅沢ポイント3選（必ず `<ul class="premium-points-list">` と `<li>` タグを使用。なぜこのスクイーズが「極上」で「贅沢」なのかを明確に伝えてください）
   - 購買意欲を促すプレミアムな太字の誘導文（<strong> または <b> タグを使用）
   - 最後にアフィリエイトリンクのボタンとして、必ずクラス名 `premium-affiliate-btn` を付与した <a>タグを配置してください。（例：`<a class="premium-affiliate-btn" href="{url}" target="_blank" rel="noopener noreferrer">プレミアム詳細を見る ＞</a>`）
"""

    system_prompt = "あなたは高級スクイーズ専門のコレクター兼紹介ブロガーです。SNSで話題の高級インポートスクイーズや、『Mellojoy』などの大人気・レア触感スクイーズを厳選して紹介します。触感フェチや大人のコレクター層に向けて、上品で洗練された、かつ商品の魅力がダイレクトに伝わる記事を日本語のみで執筆してください。毎回完全にユニークで、テンプレートの使い回し感のない文章を作成してください。指示された仕様に完全に従い、前置きやHTMLタグブロックのマークダウン表現などを含めない純粋なHTML本文のみを出力します。"

    # 1. GitHub Models API (GITHUB_TOKENを使用) を最優先
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if github_token:
        try:
            print("Attempting to generate article with GitHub Models API...")
            headers = {
                "Authorization": f"Bearer {github_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            response = requests.post("https://models.inference.ai.azure.com/chat/completions", headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()["choices"][0]["message"]["content"].strip()
                if "```html" in result:
                    result = result.split("```html", 1)[1]
                if "```" in result:
                    result = result.split("```", 1)[0]
                return result.strip()
            else:
                print(f"GitHub Models API returned status code: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"GitHub Models API failed with exception: {e}")
    else:
        print("GITHUB_TOKEN / GH_TOKEN is not set in environment variables.")

    # 2. Pollinations AI (キー不要、フォールバック)
    pollinations_models = ["openai", "mistral", "llama"]
    for model in pollinations_models:
        for attempt in range(3):  # 最大3回リトライ
            try:
                print(f"Attempting to generate article with Pollinations AI (model: {model}, attempt: {attempt + 1})...")
                response = requests.post(
                    "https://text.pollinations.ai/",
                    json={
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "model": model
                    },
                    timeout=45
                )
                if response.status_code == 200 and len(response.text.strip()) > 100:
                    result = response.text.strip()
                    if "```html" in result:
                        result = result.split("```html", 1)[1]
                    if "```" in result:
                        result = result.split("```", 1)[0]
                    return result.strip()
                elif response.status_code == 429:
                    print(f"Pollinations AI returned 429. Sleeping before retry...")
                    time.sleep(3)
                else:
                    print(f"Pollinations AI ({model}) returned status code: {response.status_code} - {response.text[:200]}")
                    break  # 429以外はリトライせず次のモデルへ
            except Exception as e:
                print(f"Pollinations AI ({model}) failed with exception: {e}")
                time.sleep(2)

    # 最終フォールバック: LLMが全滅した場合のテンプレート記事生成
    print("WARNING: All LLM generation attempts failed. Generating article using local premium template.")
    fallback_html = f"""<div class="premium-squishy-article">
    <div class="premium-image-wrapper">
        <img src="{image_url}" alt="{title}" />
    </div>
    
    <div class="premium-content-body">
        <h2 style="font-size: 20px; color: #2c2302; margin-top: 10px; margin-bottom: 15px;">【極上レア触感】{title}</h2>
        
        <p>「贅沢スクイーズLife」がお届けする、極上のリラックスアイテム。SNSで大きな話題を呼んでいる「Mellojoy」シリーズの高級インポートスクイーズをご紹介します。</p>
        
        <p>手に吸い付くような独特のもちもち感と、時間をかけてゆっくりと戻る超低反発のプレミアムな触感。ただ可愛いだけでなく、見ているだけで心が満たされる高いデザイン性が、忙しい毎日に極上の癒やしと贅沢なひとときをもたらしてくれます。</p>
        
        <ul class="premium-points-list">
            <li><strong>極上の低反発仕様：</strong> 何度も握りたくなる極上のレア触感で、大人のための上質な癒やしを提供します。</li>
            <li><strong>洗練されたインポートデザイン：</strong> お部屋のインテリアとしても美しく映える、プレミアム感溢れる仕上がり。</li>
            <li><strong>特別な香りと質感：</strong> 所有する喜びを満たしてくれる、こだわり抜かれた贅沢なクオリティ。</li>
        </ul>
        
        <p style="font-size: 15px; margin-bottom: 25px;">特別な癒やしを演出するこちらのスクイーズは、現在 <strong>{price}円</strong> でお求めいただけます。</p>
    </div>
    
    <div style="text-align: center; margin-top: 15px; margin-bottom: 10px;">
        <a class="premium-affiliate-btn" href="{url}" target="_blank" rel="noopener noreferrer">
            プレミアム詳細を見る ＞
        </a>
    </div>
</div>"""
    return fallback_html.strip()


def post_to_blogger(title, content):
    session_b64 = os.environ.get("BLOGGER_SESSION_B64")
    if not session_b64:
        raise ValueError("BLOGGER_SESSION_B64 is not set in environment variables.")
    
    try:
        decoded_str = base64.b64decode(session_b64).decode('utf-8')
        json.loads(decoded_str) # JSONとして正しいか検証
    except Exception as e:
        raise ValueError(f"BLOGGER_SESSION_B64 のデコードに失敗しました。正しいBase64文字列が設定されているか確認してください。エラー詳細: {e}")

    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    if not blog_id:
        raise ValueError("BLOGGER_BLOG_ID is not set in environment variables.")

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".json") as temp_file:
        temp_file.write(decoded_str)
        session_file_path = temp_file.name

    print(f"Posting to Blogger (Blog ID: {blog_id}) using Playwright...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                storage_state=session_file_path,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            try:
                page.goto(f"https://www.blogger.com/blog/posts/{blog_id}", wait_until="networkidle")
                time.sleep(random.uniform(3.0, 5.0))

                # 新しい投稿ボタンをクリックして作成画面へ遷移（直接URL指定だと弾かれる対策）
                new_post_btn = page.locator('a[aria-label="新しい投稿"], a[aria-label="New post"], div[aria-label="新しい投稿"], div[aria-label="New post"], span:has-text("新しい投稿"), span:has-text("New Post")').first
                new_post_btn.wait_for(state="visible", timeout=15000)
                new_post_btn.click()
                time.sleep(random.uniform(3.0, 5.0))

                title_input = page.locator('.titleField input, input[aria-label*="Title"], input[aria-label*="タイトル"], input.whsOnd.zHQkBf').first
                title_input.wait_for(state="visible", timeout=30000)
                title_input.click()
                time.sleep(random.uniform(0.5, 1.5))
                title_input.fill(title)
                time.sleep(random.uniform(1.0, 2.0))

                view_switch = page.locator('[aria-label="View mode"], [aria-label="表示モード"]').first
                if view_switch.count() > 0:
                    view_switch.click()
                    time.sleep(random.uniform(0.5, 1.0))
                    html_view_btn = page.locator('[aria-label="HTML view"], [aria-label="HTML ビュー"]').first
                    if html_view_btn.count() > 0:
                        html_view_btn.click()
                        time.sleep(random.uniform(1.0, 2.0))

                textarea = page.locator('textarea[aria-label="Body"], textarea[aria-label="本文"], .html-textarea').first
                if textarea.count() > 0:
                    textarea.click()
                    textarea.fill(content)
                else:
                    editor = page.locator('.editable, [contenteditable="true"]').first
                    editor.click()
                    page.evaluate('''(content) => {
                        document.querySelector('[contenteditable="true"]').innerHTML = content;
                    }''', content)
                    page.keyboard.press('Space')

                time.sleep(random.uniform(2.0, 3.0))

                publish_btn = page.locator('[aria-label="Publish"], [aria-label="公開"], div[role="button"]:has-text("公開"), div[role="button"]:has-text("Publish")').first
                publish_btn.wait_for(state="visible", timeout=10000)
                publish_btn.click()
                time.sleep(random.uniform(1.0, 2.0))

                confirm_btn = page.locator('[aria-label="Confirm"], [aria-label="確認"], div[role="button"]:has-text("確認"), div[role="button"]:has-text("Confirm")').first
                if confirm_btn.count() > 0:
                    confirm_btn.click()
                    time.sleep(random.uniform(2.0, 4.0))

                print("Successfully posted using Playwright!")
            except Exception as e:
                print(f"Error occurred. Current URL: {page.url}")
                print(f"Page Title: {page.title()}")
                print(f"Page Content Snippet: {page.content()[:1000]}")
                raise e

    finally:
        if os.path.exists(session_file_path):
            os.remove(session_file_path)

def main():
    try:
        # 1. 楽天から商品取得
        item = fetch_rakuten_item()
        item_code = item.get("itemCode")
        title = item.get("itemName")
        print(f"Selected Item: {title} ({item_code})")

        # 2. LLMで記事生成
        content = generate_article_with_llm(item)

        # 3. Bloggerに投稿
        post_to_blogger(title, content)

        # 4. キャッシュに保存
        save_to_cache(item_code)
        print("Process completed successfully.")

    except Exception as e:
        print(f"Error in execution: {e}")
        exit(1)

if __name__ == "__main__":
    main()
