#!/usr/bin/env python3
import asyncio
from twikit import Client
import json
import os
from datetime import datetime, timedelta
import openai
from openai import OpenAI
import markdown

class TwitterTwikitAnalyzer:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        # Twitter認証情報（環境変数から取得）
        self.twitter_username = os.getenv('TWITTER_USERNAME')
        self.twitter_email = os.getenv('TWITTER_EMAIL')  
        self.twitter_password = os.getenv('TWITTER_PASSWORD')
        
        self.client = Client('ja')
        
    async def login_twitter(self):
        """Twitterにログイン"""
        try:
            await self.client.login(
                auth_info_1=self.twitter_username,
                auth_info_2=self.twitter_email,
                password=self.twitter_password
            )
            print("Twitterログイン成功")
            return True
        except Exception as e:
            print(f"Twitterログインエラー: {e}")
            return False
    
    async def search_tweets(self, query, count=50):
        """キーワード検索でツイートを取得"""
        try:
            print(f"検索中: {query}")
            tweets = await self.client.search_tweet(query, product='Latest', count=count)
            
            tweet_data = []
            for tweet in tweets:
                # いいね1以上またはRT1以上のツイートのみ
                if tweet.favorite_count >= 1 or tweet.retweet_count >= 1:
                    tweet_data.append({
                        'account_name': tweet.user.name,
                        'username': tweet.user.screen_name,
                        'tweet_id': tweet.id,
                        'text': tweet.text,
                        'created_at': tweet.created_at,
                        'likes': tweet.favorite_count,
                        'retweets': tweet.retweet_count,
                        'replies': tweet.reply_count or 0,
                        'url': f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",
                        'search_keyword': query
                    })
            
            print(f"{query}: {len(tweet_data)}件取得")
            return tweet_data
            
        except Exception as e:
            print(f"検索エラー ({query}): {e}")
            return []
    
    async def get_user_tweets(self, username, count=20):
        """指定ユーザーのツイートを取得"""
        try:
            print(f"ユーザーツイート取得中: @{username}")
            user = await self.client.get_user_by_screen_name(username)
            tweets = await user.get_tweets('Tweets', count=count)
            
            tweet_data = []
            for tweet in tweets:
                if tweet.favorite_count >= 1 or tweet.retweet_count >= 1:
                    tweet_data.append({
                        'account_name': tweet.user.name,
                        'username': tweet.user.screen_name,
                        'tweet_id': tweet.id,
                        'text': tweet.text,
                        'created_at': tweet.created_at,
                        'likes': tweet.favorite_count,
                        'retweets': tweet.retweet_count,
                        'replies': tweet.reply_count or 0,
                        'url': f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",
                        'search_keyword': f'@{username}'
                    })
            
            print(f"@{username}: {len(tweet_data)}件取得")
            return tweet_data
            
        except Exception as e:
            print(f"ユーザーツイート取得エラー (@{username}): {e}")
            return []
    
    async def collect_all_tweets(self):
        """全てのツイートを収集"""
        all_tweets = []
        
        # 1. キーワード検索
        search_queries = [
            '山田太郎 議員',
            '山田太郎 参議院',
            '表現の自由 山田太郎',
            '著作権 山田太郎',
            'クリエイター 山田太郎'
        ]
        
        for query in search_queries:
            tweets = await self.search_tweets(query, count=30)
            all_tweets.extend(tweets)
            await asyncio.sleep(2)  # レート制限回避
        
        # 2. 重要アカウントの直接取得
        important_users = [
            'yamadataro43',  # 山田太郎議員
        ]
        
        for username in important_users:
            tweets = await self.get_user_tweets(username, count=50)
            all_tweets.extend(tweets)
            await asyncio.sleep(2)
        
        # 重複削除
        seen_ids = set()
        unique_tweets = []
        for tweet in all_tweets:
            if tweet['tweet_id'] not in seen_ids:
                seen_ids.add(tweet['tweet_id'])
                unique_tweets.append(tweet)
        
        # エンゲージメント順にソート
        return sorted(unique_tweets, key=lambda x: x['likes'] + x['retweets'], reverse=True)
    
    def analyze_tweets_with_ai(self, tweets):
        """AIでツイートを分析"""
        if not tweets:
            return "ツイートが見つかりませんでした。"
        
        # 上位20件を分析
        tweet_texts = []
        for tweet in tweets[:20]:
            tweet_texts.append(f"@{tweet['username']}: {tweet['text']} (👍{tweet['likes']} 🔄{tweet['retweets']})")
        
        prompt = f"""以下は山田太郎議員に関連するツイートです。
分野ごとに整理して、リポスト・ウォッチ候補として分類してください。

## 分野別ツイート一覧

### 📝 表現の自由・規制関連
（該当ツイートを元の文章のまま箇条書き）

### 💻 デジタル・IT政策  
（該当ツイートを元の文章のまま箇条書き）

### 🎨 クリエイター・コンテンツ
（該当ツイートを元の文章のまま箇条書き）

### ⚖️ 法案・政策提案
（該当ツイートを元の文章のまま箇条書き）

### 🗳️ 政治活動・選挙
（該当ツイートを元の文章のまま箇条書き）

### 📊 その他
（該当ツイートを元の文章のまま箇条書き）

ツイート一覧：
{chr(10).join(tweet_texts)}"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI分析エラー: {e}"
    
    async def generate_report(self):
        """レポート生成のメイン処理"""
        print("=== Twikit版 Twitter分析開始 ===")
        
        # Twitterログイン
        if not await self.login_twitter():
            print("ログインに失敗しました")
            return
        
        # ツイート収集
        print("ツイート収集中...")
        all_tweets = await self.collect_all_tweets()
        print(f"総取得数: {len(all_tweets)}件")
        
        # AI分析
        print("AI分析中...")
        analysis = self.analyze_tweets_with_ai(all_tweets)
        
        # レポート生成
        report_date = datetime.now().strftime('%Y-%m-%d')
        report_content = f"""# 🔍 山田太郎議員関連ツイート拾い上げ (Twikit版)
## {report_date}

### 📈 収集状況  
- 📊 取得ツイート総数: {len(all_tweets)}件
- 🚀 **API制限なしで大量取得成功**

{analysis}

---

## 🔥 リポスト・ウォッチ候補ツイート
*エンゲージメントが高い順に表示*

"""
        
        # 上位20件の詳細表示
        for tweet in all_tweets[:20]:
            report_content += f"""
### 📱 [{tweet['account_name']}]({tweet['url']})
**👍{tweet['likes']} 🔄{tweet['retweets']} 💬{tweet['replies']}** | {tweet['created_at'].strftime('%m/%d %H:%M') if hasattr(tweet['created_at'], 'strftime') else tweet['created_at']} | 📍 `{tweet['search_keyword']}`

> {tweet['text']}

<a href="{tweet['url']}">🔗 Xで原文を見る（リポスト可能）</a>

---
"""
        
        # ファイル出力
        os.makedirs('reports', exist_ok=True)
        
        with open(f'reports/twikit_report_{report_date}.md', 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # HTML版も生成
        html_content = markdown.markdown(report_content)
        with open(f'reports/twikit_report_{report_date}.html', 'w', encoding='utf-8') as f:
            f.write(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>山田太郎議員ツイート分析 - {report_date}</title>
    <style>
        body {{ font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        blockquote {{ background: #f5f5f5; padding: 10px; border-left: 4px solid #ddd; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>""")
        
        print(f"Twikitレポートを生成しました: reports/twikit_report_{report_date}.html")

if __name__ == "__main__":
    analyzer = TwitterTwikitAnalyzer()
    asyncio.run(analyzer.generate_report())