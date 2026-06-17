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
        
        # localStorageのバイナリデータによるエラーを防ぐため、cookieのみを抽出
        minimal_state = {"cookies": state.get("cookies", [])}
        
        with open("session.json", "w", encoding="utf-8") as f:
            json.dump(minimal_state, f)
            
        print("session.json を作成しました。")
        
        import base64
        import subprocess
        
        b64_str = base64.b64encode(json.dumps(minimal_state).encode('utf-8')).decode('utf-8')
        
        try:
            process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
            process.communicate(b64_str.encode('utf-8'))
            print("\n★★★ Base64文字列をMacのクリップボードに自動コピーしました！ ★★★")
            print("そのままGitHub Secretsの設定画面で [Command + V] を押して貼り付けてください。")
            print("=========================================================")
        except Exception as e:
            print("自動コピーに失敗しました。以下の文字列を漏れなく全て手動でコピーしてください：\n")
            print(b64_str)
            print("\n=========================================================")

        browser.close()

if __name__ == "__main__":
    main()
