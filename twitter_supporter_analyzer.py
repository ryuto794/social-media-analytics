#!/usr/bin/env python3
import tweepy
import openai
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import markdown

class TwitterSupporterAnalyzer:
    def __init__(self):
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Twitter API v2 client
        self.twitter_client = tweepy.Client(bearer_token=self.twitter_bearer_token)
        
        # OpenAI client
        from openai import OpenAI
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        # 支援者アカウントリスト（設定ファイルから読み込み）
        self.supporter_accounts = self.load_supporter_accounts()
    
    def load_supporter_accounts(self):
        """支援者アカウントリストを設定ファイルから読み込み"""
        try:
            with open('supporter_accounts.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def get_viral_tweets(self, days_back=1):
        """バイラルツイートを収集"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        viral_tweets = []
        
        for account in self.supporter_accounts:
            try:
                # ユーザーのツイートを取得
                tweets = tweepy.Paginator(
                    self.twitter_client.get_users_tweets,
                    id=account['user_id'],
                    start_time=start_time,
                    end_time=end_time,
                    tweet_fields=['public_metrics', 'created_at', 'author_id'],
                    max_results=100
                ).flatten(limit=100)
                
                for tweet in tweets:
                    metrics = tweet.public_metrics
                    # バイラル判定（いいね50以上 または RT20以上）
                    if metrics['like_count'] >= 50 or metrics['retweet_count'] >= 20:
                        viral_tweets.append({
                            'account_name': account['name'],
                            'username': account['username'],
                            'tweet_id': tweet.id,
                            'text': tweet.text,
                            'created_at': tweet.created_at,
                            'likes': metrics['like_count'],
                            'retweets': metrics['retweet_count'],
                            'replies': metrics['reply_count'],
                            'url': f"https://twitter.com/{account['username']}/status/{tweet.id}"
                        })
                        
            except Exception as e:
                print(f"Error fetching tweets for {account['name']}: {e}")
                continue
        
        return sorted(viral_tweets, key=lambda x: x['likes'] + x['retweets'], reverse=True)
    
    def analyze_tweets_with_ai(self, tweets):
        """AIでツイートを分析・要約"""
        if not tweets:
            return "本日はバイラルツイートはありませんでした。"
        
        # ツイート内容を整理
        tweet_texts = []
        for tweet in tweets[:20]:  # 上位20件を分析
            tweet_texts.append(f"@{tweet['username']}: {tweet['text']} (👍{tweet['likes']} 🔄{tweet['retweets']})")
        
        prompt = f"""以下は山田太郎議員の支援者による本日のバイラルツイートです。
これらのツイートを分析し、以下の観点で日本語でまとめてください：

1. 主要なトピック・テーマ
2. 支援者の関心事
3. 特に注目すべきツイート（3-5件）
4. 全体的な傾向

ツイート一覧：
{chr(10).join(tweet_texts)}

分析結果を読みやすいマークダウン形式で出力してください。"""

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
    
    def generate_report(self):
        """レポートを生成"""
        print("バイラルツイートを収集中...")
        viral_tweets = self.get_viral_tweets()
        
        print(f"{len(viral_tweets)}件のバイラルツイートを発見")
        
        print("AI分析を実行中...")
        analysis = self.analyze_tweets_with_ai(viral_tweets)
        
        # レポート生成
        report_date = datetime.now().strftime('%Y-%m-%d')
        report_content = f"""# 山田太郎議員支援者ツイート分析レポート
## {report_date}

{analysis}

## 詳細データ
"""
        
        # 詳細ツイート情報を追加
        for tweet in viral_tweets[:10]:
            report_content += f"""
### [{tweet['account_name']}](https://twitter.com/{tweet['username']})
- **ツイート**: {tweet['text']}
- **エンゲージメント**: 👍{tweet['likes']} 🔄{tweet['retweets']} 💬{tweet['replies']}
- **URL**: {tweet['url']}
- **投稿時刻**: {tweet['created_at']}

---
"""
        
        # reportsディレクトリを作成
        os.makedirs('reports', exist_ok=True)
        
        # HTMLファイルとして保存
        html_content = markdown.markdown(report_content)
        
        with open(f'reports/report_{report_date}.md', 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        with open(f'reports/report_{report_date}.html', 'w', encoding='utf-8') as f:
            f.write(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>支援者ツイート分析レポート - {report_date}</title>
    <style>
        body {{ font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .tweet {{ background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 8px; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>""")
        
        print(f"レポートを生成しました: reports/report_{report_date}.html")
        return report_content

if __name__ == "__main__":
    analyzer = TwitterSupporterAnalyzer()
    analyzer.generate_report()