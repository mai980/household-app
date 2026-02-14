# アーキテクチャ図 — カップル家計簿

## システム全体構成

```mermaid
graph TB
    subgraph Client["📱 クライアント"]
        SA["スマートフォン A<br/>(たう)"]
        SB["スマートフォン B<br/>(萌伽)"]
    end

    subgraph Render["☁️ Render.com"]
        direction TB
        subgraph WebService["Web Service"]
            GU["Gunicorn<br/>(WSGI Server)"]
            FL["Flask App<br/>(app.py)"]
            MD["Models<br/>(models.py)"]
            TP["Templates<br/>(Jinja2 / Bootstrap 5)"]
        end
        PG[("PostgreSQL<br/>Database")]
    end

    SA -- "HTTPS" --> GU
    SB -- "HTTPS" --> GU
    GU --> FL
    FL --> MD
    FL --> TP
    MD -- "SQLAlchemy ORM" --> PG
```

## リクエストフロー

```mermaid
sequenceDiagram
    participant U as 📱 ユーザー
    participant G as Gunicorn
    participant F as Flask (app.py)
    participant M as Models (models.py)
    participant DB as PostgreSQL

    U->>G: HTTPS リクエスト
    G->>F: WSGI 転送

    alt GET / (ダッシュボード)
        F->>M: _calculate_balance()
        M->>DB: SELECT * FROM transactions
        DB-->>M: 全レコード
        M-->>F: 清算結果
        F-->>U: dashboard.html
    end

    alt POST /add (支出登録)
        F->>M: Transaction(...) 作成
        M->>DB: INSERT INTO transactions
        DB-->>M: OK
        F-->>U: 302 → ダッシュボード
    end
```

## レイヤー構成

```mermaid
graph LR
    subgraph Presentation["プレゼンテーション層"]
        B5["Bootstrap 5<br/>CSS / JS"]
        JJ["Jinja2<br/>テンプレート"]
    end

    subgraph Application["アプリケーション層"]
        RT["ルーティング"]
        BL["清算ロジック"]
        VL["バリデーション"]
    end

    subgraph Data["データ層"]
        SA["SQLAlchemy ORM"]
        PG["PostgreSQL<br/>(本番)"]
        SL["SQLite<br/>(ローカル)"]
    end

    B5 --> JJ
    JJ --> RT
    RT --> BL
    RT --> VL
    BL --> SA
    VL --> SA
    SA --> PG
    SA -.-> SL
```

## ファイル構成マップ

```
household_app/
├── app/
│   ├── __init__.py          ← パッケージ初期化
│   ├── app.py               ← Flask ルーティング・清算ロジック
│   ├── models.py            ← SQLAlchemy モデル・定数
│   ├── templates/
│   │   ├── base.html        ← 共通レイアウト (Bootstrap 5)
│   │   ├── dashboard.html   ← ダッシュボード
│   │   ├── add_transaction.html  ← 支出登録
│   │   ├── edit_transaction.html ← 支出編集
│   │   └── history.html     ← 履歴一覧
│   └── static/
│       ├── css/style.css    ← カスタムスタイル
│       └── js/main.js       ← フロントエンドJS
├── requirements.txt
├── Procfile
└── DOCS_*.md
```

## 環境別 DB 切り替え

| 環境 | DATABASE_URL 環境変数 | 使用 DB |
|------|----------------------|---------|
| ローカル開発 | 未設定 | SQLite (`instance/household.db`) |
| Render.com 本番 | 設定済み | PostgreSQL |
