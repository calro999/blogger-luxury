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

    keyword = "サンリオ レア"
    print(f"Searching Rakuten for keyword: {keyword}")

    url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "keyword": keyword,
        "format": "json",
        "hits": 30
    }

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
    title = item.get("itemName")
    price = item.get("itemPrice")
    url = item.get("affiliateUrl") or item.get("itemUrl")
    
    # 複数画像がある場合は最初の一枚、なければ空文字列
    image_url = ""
    medium_images = item.get("mediumImageUrls", [])
    if medium_images:
        img_obj = medium_images[0]
        image_url = img_obj.get("imageUrl", "") if isinstance(img_obj, dict) else img_obj
    else:
        # fallback
        small_images = item.get("smallImageUrls", [])
        if small_images:
            img_obj = small_images[0]
            image_url = img_obj.get("imageUrl", "") if isinstance(img_obj, dict) else img_obj

    if image_url:
        # 楽天画像URLのサイズ指定パラメータ (?_ex=128x128 等) を置換して大きいサイズにする
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
     * コンセプト「日本未発売の海外限定モデルや、即完売した周年記念のぬいぐるみなど、今では入手困難な『お宝級の激レアかわいいサンリオグッズ』だけを厳選」に完全に合致した内容にしてください。
     * ターゲット層（かわいいものが好きな小さな女の子から大人の女性まで）に響く、上品で高級感にあふれ、コレクター心をくすぐるようなワクワクする日本語の紹介文にしてください。
     * 客観的にその商品の希少性やデザインの美しさを語り、過度な自分語りやポエム調の表現は避けてください。
     * 毎回完全に独立したユニークな内容とし、他の記事と似たような言い回しやテンプレート的な文章構成の使い回しは絶対に禁止します。商品の個別の特徴（限定の理由、コラボ、衣装、特別な表情など）に焦点を当てて執筆してください。
   - コレクター心をくすぐるお宝ポイント3選（必ず <ul> と <li> タグを使用。なぜこのグッズが「お宝級」で「激レア」なのかを明確に伝えてください）
   - 購買意欲を促す太字の誘導文（<strong> または <b> タグを使用）
   - 最後にアフィリエイトリンクのボタン（<a>タグでスタイルし、新しいタブで開く target="_blank" rel="noopener noreferrer" を指定。上品でかわいい高級感のあるデザインになるようインラインスタイルを施すこと。ピンクやローズ、ゴールドを基調とした、洗練されたグラデーションやシャドウを施したボタンにしてください。例：background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: bold; box-shadow: 0 4px 15px rgba(255, 154, 158, 0.4); border: 1px solid rgba(255, 255, 255, 0.3);）
"""

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
                    {"role": "system", "content": "あなたは『お宝級の激レアかわいいサンリオグッズ』専門のコレクター兼紹介ブロガーです。日本未発売の海外限定モデルや即完売した周年記念のぬいぐるみなど、今では入手困難なサンリオグッズを厳選して紹介します。ターゲットである『かわいいものが好きな小さな女の子から大人の女性』に向けて、上品で高級感があり、かつワクワクするような魅力的な記事を日本語のみで執筆してください。毎回完全にユニークで、テンプレートの使い回し感のない文章を作成してください。指示された仕様に完全に従い、前置きやHTMLタグブロックのマークダウン表現などを含めない純粋なHTML本文のみを出力します。"},
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
    pollinations_models = ["openai", "mistral"]
    for model in pollinations_models:
        try:
            print(f"Attempting to generate article with Pollinations AI (model: {model})...")
            response = requests.post(
                "https://text.pollinations.ai/",
                json={
                    "messages": [
                        {"role": "system", "content": "あなたは『お宝級の激レアかわいいサンリオグッズ』専門のコレクター兼紹介ブロガーです。日本未発売の海外限定モデルや即完売した周年記念のぬいぐるみなど、今では入手困難なサンリオグッズを厳選して紹介します。ターゲットである『かわいいものが好きな小さな女の子から大人の女性』に向けて、上品で高級感があり、かつワクワクするような魅力的な記事を日本語のみで執筆してください。毎回完全にユニークで、テンプレートの使い回し感のない文章を作成してください。指示された仕様に完全に従い、前置きやHTMLタグブロックのマークダウン表現などを含めない純粋なHTML本文のみを出力します。"},
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
            else:
                print(f"Pollinations AI ({model}) returned status code: {response.status_code} - {response.text[:200]}")
        except Exception as e:
            print(f"Pollinations AI ({model}) failed with exception: {e}")
            time.sleep(1)

    raise RuntimeError("All LLM generation attempts failed.")

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
