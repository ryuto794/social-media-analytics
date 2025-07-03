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
    
    def get_viral_tweets(self, days_back=7):
        """バイラルツイートを収集（最新から優先）"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        viral_tweets = []
        
        for account in self.supporter_accounts:
            try:
                # 最新のツイートから取得（時系列順）
                tweets = self.twitter_client.get_users_tweets(
                    id=account['user_id'],
                    start_time=start_time,
                    end_time=end_time,
                    tweet_fields=['public_metrics', 'created_at', 'author_id'],
                    max_results=100  # 最新100件を取得
                )
                
                if tweets.data:
                    # 最新のツイートから順番に処理
                    for tweet in tweets.data:
                        metrics = tweet.public_metrics
                        # 注目ツイート判定（いいね3以上 または RT2以上 または 返信5以上）
                        if metrics['like_count'] >= 3 or metrics['retweet_count'] >= 2 or metrics['reply_count'] >= 5:
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
        
        # 最新の投稿順にソート（作成日時が新しい順）
        return sorted(viral_tweets, key=lambda x: x['created_at'], reverse=True)
    
    def filter_relevant_tweets(self, tweets):
        """山田太郎議員関連キーワードでツイートをフィルタリング"""
        yamada_keywords = [
            '山田太郎', '表現の自由', '著作権', 'クリエイター', 'DX', 'デジタル',
            '児童ポルノ', '児ポ', '非実在', '表現規制', 'CODA', 'TPP',
            'コンテンツ', 'アニメ', 'マンガ', 'ゲーム', '同人', 'オタク',
            'IT政策', 'デジタル庁', 'マイナンバー', 'サイバー', 'AI規制',
            '参議院', '自民党', '政治', '議員', '政策', '法案'
        ]
        
        relevant_tweets = []
        for tweet in tweets:
            text = tweet['text'].lower()
            # キーワードマッチング
            if any(keyword.lower() in text for keyword in yamada_keywords):
                tweet['relevance_score'] = sum(1 for keyword in yamada_keywords if keyword.lower() in text)
                relevant_tweets.append(tweet)
        
        # 関連度順にソート
        relevant_tweets.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # 関連ツイートがない場合は元のリストを返す
        return relevant_tweets if relevant_tweets else tweets

    def analyze_tweets_with_ai(self, tweets):
        """AIでツイートを分析・要約"""
        if not tweets:
            return "本日はバイラルツイートはありませんでした。"
        
        # 関連ツイートをフィルタリング
        filtered_tweets = self.filter_relevant_tweets(tweets)
        
        # ツイート内容を整理
        tweet_texts = []
        for tweet in filtered_tweets[:20]:  # 上位20件を分析
            relevance = f"(関連度: {tweet.get('relevance_score', 0)})" if 'relevance_score' in tweet else ""
            tweet_texts.append(f"@{tweet['username']}: {tweet['text']} (👍{tweet['likes']} 🔄{tweet['retweets']}) {relevance}")
        
        prompt = f"""以下は山田太郎議員に関連するツイートです。
手動チェックの効率化のため、重要なツイートを分野別に分類してリストアップしてください。
要約は不要です。元のツイート内容をそのまま残して分類してください。

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
{chr(10).join(tweet_texts)}

各ツイートを適切な分野に振り分けて、原文のまま表示してください。"""

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
        
        # 関連ツイートをフィルタリング
        relevant_tweets = self.filter_relevant_tweets(viral_tweets)
        print(f"山田太郎議員関連: {len(relevant_tweets)}件")
        
        print("AI分析を実行中...")
        analysis = self.analyze_tweets_with_ai(viral_tweets)
        
        # レポート生成
        report_date = datetime.now().strftime('%Y-%m-%d')
        report_content = f"""# 🔍 山田太郎議員関連ツイート拾い上げ
## {report_date}

### 📈 収集状況  
- 📊 注目ツイート総数: {len(viral_tweets)}件
- 🎯 関連ツイート: {len(relevant_tweets)}件
- 🚀 **リポスト・ウォッチ候補を効率的に発見**

{analysis}

---

## 🔥 リポスト・ウォッチ候補ツイート
*エンゲージメントが高い順に表示（クリックでXへ移動）*

"""
        
        # 関連度の高いツイートを優先表示
        display_tweets = relevant_tweets[:10] if relevant_tweets else viral_tweets[:10]
        for tweet in display_tweets:
            relevance_info = f"🎯**{tweet.get('relevance_score', 0)}点** " if 'relevance_score' in tweet else ""
            report_content += f"""
### 📱 [{tweet['account_name']}]({tweet['url']}) {relevance_info}
**👍{tweet['likes']} 🔄{tweet['retweets']} 💬{tweet['replies']}** | {tweet['created_at'].strftime('%m/%d %H:%M')}

> {tweet['text']}

<blockquote class="twitter-tweet">
<a href="{tweet['url']}">🔗 Xで原文を見る（リポスト可能）</a>
</blockquote>

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