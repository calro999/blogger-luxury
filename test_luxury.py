import os
import sys
from luxury_blogger import generate_article_with_llm

def test_main():
    print("Starting verification test for blogger-luxury (LLM generation only)...")
    
    # GITHUB_TOKEN または GH_TOKEN が設定されているか確認（ない場合はPollinations AIがフォールバックとして使われます）
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not github_token:
        print("Notice: GITHUB_TOKEN is not set. Will fallback to Pollinations AI (mistral/openai).")

    # ダミー商品データ (MELLOJOYスクイーズ)
    dummy_item = {
        "itemName": "【Mellojoy】超低反発 プレミアムデカ桃スクイーズ レア限定モデル (香り付き)",
        "itemPrice": "5800",
        "itemUrl": "https://item.rakuten.co.jp/dummy/mellojoy-peach/",
        "affiliateUrl": "https://hb.afl.rakuten.co.jp/hgc/dummy/?pc=https%3A%2F%2Fitem.rakuten.co.jp%2Fdummy%2Fmellojoy-peach%2F",
        "mediumImageUrls": ["https://thumbnail.image.rakuten.co.jp/@0_mall/dummy/cabinet/mellojoy_peach.jpg"]
    }
        
    try:
        # LLMで記事生成
        print("Generating article with LLM...")
        content = generate_article_with_llm(dummy_item)
        
        print("\n=== GENERATED ARTICLE HTML ===")
        print(content)
        print("==============================\n")
        print("Verification completed successfully!")

    except Exception as e:
        print(f"Error during verification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_main()
