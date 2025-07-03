# 山田太郎議員支援者ツイート分析ツール

## 概要
山田太郎議員の支援者によるバイラルツイートを自動収集・AI分析し、日次レポートを生成するツールです。

## 技術構成
- **言語**: Python 3.9
- **実行環境**: GitHub Actions（無料枠）
- **API**: Twitter API v2 Basic（無料）、OpenAI API（月5ドル程度）
- **ホスティング**: GitHub Pages（無料）

## セットアップ手順

### 1. リポジトリの準備
```bash
# リポジトリをクローン
git clone <your-repo-url>
cd ego-search

# 依存関係をインストール（ローカルテスト用）
pip install -r requirements.txt
```

### 2. API キーの取得

#### Twitter API v2
1. [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)でアカウント作成
2. 新しいアプリを作成
3. **Bearer Token**を取得

#### OpenAI API
1. [OpenAI Platform](https://platform.openai.com/)でアカウント作成
2. API キーを生成
3. 課金設定（月5ドル程度の制限推奨）

### 3. GitHub Secrets の設定
リポジトリの Settings > Secrets and variables > Actions で以下を設定：

- `TWITTER_BEARER_TOKEN`: Twitter API Bearer Token
- `OPENAI_API_KEY`: OpenAI API キー

### 4. 支援者アカウントの設定
`supporter_accounts.json`を編集：

```json
[
  {
    "name": "支援者の表示名",
    "username": "twitterのusername",
    "user_id": "TwitterのユーザーID",
    "description": "説明"
  }
]
```

**ユーザーIDの取得方法**：
- [Twitter ID取得ツール](https://tweeterid.com/)を使用
- または Python で取得：
```python
import tweepy
client = tweepy.Client(bearer_token="YOUR_BEARER_TOKEN")
user = client.get_user(username="username")
print(user.data.id)
```

### 5. GitHub Pages の有効化
1. リポジトリの Settings > Pages
2. Source を "Deploy from a branch" に設定
3. Branch を "gh-pages" に設定

## 運用方法

### 自動実行
- 毎日午前6時（JST）に自動実行
- GitHub Actions で処理後、GitHub Pages に結果を公開

### 手動実行
1. GitHub の Actions タブ
2. "Daily Twitter Analysis" ワークフロー
3. "Run workflow" ボタンで実行

### ローカルテスト
```bash
export TWITTER_BEARER_TOKEN="your_token"
export OPENAI_API_KEY="your_key"
python twitter_supporter_analyzer.py
```

## 出力内容

### 分析レポート
- **主要トピック**: 支援者が注目している話題
- **バイラルツイート**: いいね50以上またはRT20以上
- **AI要約**: GPT-4o-miniによる傾向分析
- **詳細データ**: 各ツイートの詳細情報

### 公開URL
`https://your-username.github.io/ego-search/`

## カスタマイズ

### バイラル判定基準の変更
`twitter_supporter_analyzer.py`の以下を修正：
```python
# 現在: いいね50以上 または RT20以上
if metrics['like_count'] >= 50 or metrics['retweet_count'] >= 20:
```

### 実行頻度の変更
`.github/workflows/daily_analysis.yml`のcron設定を変更：
```yaml
schedule:
  - cron: '0 21 * * *'  # 毎日午前6時（JST）
```

### AI分析の調整
`analyze_tweets_with_ai`メソッドのpromptを修正

## コスト試算

### 無料枠
- GitHub Actions: 月2000分
- Twitter API v2 Basic: 月10万ツイート
- GitHub Pages: 無料

### 有料部分
- OpenAI API: 月5ドル程度（1日1回実行想定）

### 合計月額コスト
**約500円**（OpenAI APIのみ）

## トラブルシューティング

### よくある問題

1. **Twitter API制限**
   - 15分間の制限に達した場合は時間をおいて再実行
   - 支援者アカウント数を調整

2. **OpenAI API制限**
   - 課金制限に達した場合は制限額を調整
   - モデルをgpt-3.5-turboに変更して コスト削減

3. **GitHub Actions失敗**
   - Secrets の設定確認
   - ログでエラー詳細を確認

### デバッグ方法
```bash
# ローカルで実行して詳細ログを確認
python twitter_supporter_analyzer.py
```

## セキュリティ注意事項
- API キーは絶対にコードに直接書かない
- GitHub Secrets を使用
- 定期的にAPI キーをローテーション

## 機能拡張アイデア
- Slack/Discord通知機能
- 感情分析の追加
- 画像付きツイートの分析
- 過去データとの比較分析