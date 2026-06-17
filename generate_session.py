import os
import json
from playwright.sync_api import sync_playwright

def main():
    print("Bloggerにログインしてセッションを保存します...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page.goto("https://www.blogger.com/")
        print("=========================================================")
        print("ブラウザ上でGoogleアカウントにログインしてください。")
        print("ログインが完了し、【Bloggerの自分のブログ管理画面】が完全に表示されたら、")
        print("このターミナルで Enter キーを押してください。")
        print("※絶対に手動でブラウザのタブやウィンドウを閉じないでください！")
        print("=========================================================")
        input("Press Enter to continue after login...")
        
        state = context.storage_state()
        
        with open("session.json", "w") as f:
            json.dump(state, f)
            
        print("session.json を作成しました。")
        print("このファイルの内容をBase64エンコードし、GitHub Secrets の BLOGGER_SESSION_B64 に設定してください。")
        print("\nBase64エンコードコマンド（Macの場合）:")
        print("base64 -i session.json | pbcopy")

        browser.close()

if __name__ == "__main__":
    main()
