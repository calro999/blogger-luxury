import os
import random
import re
import requests
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

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

    if image_url:
        image_url = re.sub(r'\?_ex=\d+x\d+', '?_ex=500x500', image_url)

    prompt = f"""以下の楽天の商品情報を基にして、自動投稿用のHTML記事を生成してください。
【商品名】: {title}
【価格】: {price}円
【商品画像URL】: {image_url}
【アフィリエイトURL】: {url}

以下の要件を厳格に遵守してください：
1. 出力はブログの本文となるHTMLコードのみとし、余計な説明、挨拶、前置きや後書き（例：「以下が記事です」「```html」のようなマークダウンブロック）は絶対に含めず、純粋なHTML文字列のみを出力してください。
2. 日本語のみで出力してください。
3. アイキャッチ画像として、商品画像URL（{image_url}）を直接<img>タグ of src属性に指定し、記事の最上部に配置してください。
4. 記事構成：
   - キャッチーで見出しとしてふさわしい上品なタイトル（<h2> または <h3> タグを使用）
   - 商品の魅力的な説明：
     * コンセプト「贅沢スクイーズLife 〜SNSで話題の高級インポート＆レア触感カタログ〜」に完全に合致した内容にしてください。
     * 特に「Mellojoy」のスクイーズやレア感の高い高級スクイーズにフォーカスし、その極上の触感（もちもち、ふわふわ、低反発など）、SNSでの話題性、インポート品ならではの贅沢感と所有欲を満たす上品でプレミアムな魅力を伝える日本語の紹介文にしてください。
     * 客観的にその商品のデザインの美しさや品質の高さ、レア度を語り、過度な自分語りやポエム調の表現は避けてください。
     * 毎回完全に独立したユニークな内容とし、他の記事と似たような言い回しやテンプレート的な文章構成の使い回しは絶対に禁止します。商品の個別の特徴（デザイン、触感のこだわり、パッケージ、香りなど）に焦点を当てて執筆してください。
   - 極上の贅沢ポイント3選（必ず <ul> と <li> タグを使用。なぜこのスクイーズが「極上」で「贅沢」なのか、触感やデザイン、レア度の観点から明確に伝えてください）
   - 購買意欲を促すプレミアムな太字の誘導文（<strong> または <b> タグを使用）
   - 最後にアフィリエイトリンクのボタン（<a>タグでスタイルし、新しいタブで開く target="_blank" rel="noopener noreferrer" を指定。ゴールドやシャンパンゴールド、ブロンズなどの上品で洗練された高級感のあるグラデーションとシャドウを施したボタンにしてください。例：background: linear-gradient(135deg, #d4af37 0%, #f9e8a2 100%); color: #4a3c00; padding: 12px 24px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: bold; box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4); border: 1px solid rgba(255, 255, 255, 0.4);）
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
    fallback_html = f"""<div class="premium-squishy-article" style="font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; line-height: 1.8;">
    <img src="{image_url}" alt="{title}" style="max-width: 100%; height: auto; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); margin-bottom: 25px; display: block; margin-left: auto; margin-right: auto;" />
    
    <h2 style="font-size: 24px; color: #4a3c00; border-bottom: 2px solid #d4af37; padding-bottom: 10px; margin-bottom: 20px;">【プレミアム触感】{title}</h2>
    
    <p>「贅沢スクイーズLife」がお届けする、極上のリラックスアイテム。SNSで大きな話題を呼んでいる「Mellojoy」シリーズの高級インポートスクイーズをご紹介します。</p>
    
    <p>手に吸い付くような独特のもちもち感と、時間をかけてゆっくりと戻る超低反発のプレミアムな触感。ただ可愛いだけでなく、見ているだけで心が満たされる高いデザイン性が、忙しい毎日に極上の癒やしと贅沢なひとときをもたらしてくれます。</p>
    
    <h3 style="font-size: 18px; color: #4a3c00; margin-top: 30px;">極上の贅沢ポイント3選</h3>
    <ul style="padding-left: 20px; margin-bottom: 25px;">
        <li style="margin-bottom: 10px;"><strong>極上の低反発仕様：</strong> 何度も握りたくなる極上のレア触感で、大人のための上質な癒やしを提供します。</li>
        <li style="margin-bottom: 10px;"><strong>洗練されたインポートデザイン：</strong> お部屋のインテリアとしても美しく映える、プレミアム感溢れる仕上がり。</li>
        <li style="margin-bottom: 10px;"><strong>特別な香りと質感：</strong> 所有する喜びを満たしてくれる、こだわり抜かれた贅沢なクオリティ。</li>
    </ul>
    
    <p style="font-size: 16px; margin-bottom: 30px;">特別な癒やしを演出するこちらのスクイーズは、現在 <strong>{price}円</strong> でお求めいただけます。</p>
    
    <div style="text-align: center; margin-top: 35px; margin-bottom: 20px;">
        <a href="{url}" target="_blank" rel="noopener noreferrer" style="background: linear-gradient(135deg, #d4af37 0%, #f9e8a2 100%); color: #4a3c00; padding: 14px 28px; text-decoration: none; border-radius: 30px; display: inline-block; font-weight: bold; box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4); border: 1px solid rgba(255, 255, 255, 0.4); transition: transform 0.2s ease;">
            プレミアム詳細を見る ＞
        </a>
    </div>
</div>"""
    return fallback_html.strip()

def post_to_blogger(title, content):
    creds = Credentials(
        token=None,
        refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"],
        client_id=os.environ["BLOGGER_CLIENT_ID"],
        client_secret=os.environ["BLOGGER_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    service = build("blogger", "v3", credentials=creds)
    
    blog_id = os.environ["BLOGGER_BLOG_ID"]
    body = {
        "title": title,
        "content": content
    }
    
    print(f"Posting to Blogger (Blog ID: {blog_id})...")
    post = service.posts().insert(blogId=blog_id, body=body).execute()
    print(f"Successfully posted! Post URL: {post.get('url')}")

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
