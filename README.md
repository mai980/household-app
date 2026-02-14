# カップル家計簿 Web アプリケーション

カップル（2人）間の支出管理・割り勘・立て替え清算 Web アプリです。  
「最終的にどちらがどちらにいくら支払えば清算できるか」が即座にわかります。

## 🚀 セットアップ手順

### 前提条件
- Python 3.9 以上

### 1. リポジトリのクローン & 移動
```bash
cd household_app
```

### 2. 仮想環境の作成・有効化
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

### 4. アプリの起動
```bash
python app/app.py
```

ブラウザで [http://localhost:5000](http://localhost:5000) を開いてください。

## 📁 プロジェクト構成
```
household_app/
├── app/
│   ├── app.py              # Flask メインアプリ
│   ├── models.py            # SQLAlchemy モデル
│   ├── instance/            # SQLite DB (自動生成)
│   ├── templates/           # Jinja2 テンプレート
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── add_transaction.html
│   │   ├── edit_transaction.html
│   │   └── history.html
│   └── static/
│       ├── css/style.css
│       └── js/main.js
├── requirements.txt
├── Procfile
├── README.md
└── DOCS_*.md               # ドキュメント群
```

## 🌐 デプロイ (Render.com / Heroku)

### Render.com
1. GitHub リポジトリを接続
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `gunicorn app.app:app --bind 0.0.0.0:$PORT`

### Heroku
```bash
heroku create
git push heroku main
```

## 📝 ライセンス
MIT License
