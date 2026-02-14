# -*- coding: utf-8 -*-
"""
models.py - データベースモデル定義

カップル家計簿アプリのデータモデルを定義します。
"""

from datetime import date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ========================================
# 定数定義
# ========================================

# ユーザーリスト (固定2名)
USERS = ["たう", "萌伽"]

# カテゴリ一覧
CATEGORIES = [
    ("food", "🍽️ 食費"),
    ("utility", "💡 光熱費"),
    ("housing", "🏠 住居費"),
    ("transport", "🚃 交通費"),
    ("travel", "✈️ 旅行"),
    ("entertainment", "🎉 娯楽"),
    ("health", "💊 医療・健康"),
    ("shopping", "🛍️ 日用品"),
    ("other", "📌 その他"),
]

# 支払い種別
PAYMENT_TYPES = [
    ("self", "自分用"),        # 清算対象外
    ("partner", "相手用"),     # 相手が全額支払うべき（貸し）
    ("split", "割り勘"),       # 2人で等分
]


class Transaction(db.Model):
    """支出レコードモデル"""

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    title = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # 金額 (円)
    payer = db.Column(db.String(50), nullable=False)  # 支払った人
    category = db.Column(db.String(50), nullable=False, default="other")
    payment_type = db.Column(db.String(20), nullable=False, default="split")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), onupdate=db.func.now()
    )

    def __repr__(self):
        return f"<Transaction {self.id}: {self.title} ¥{self.amount:,}>"

    @property
    def category_label(self):
        """カテゴリの表示名を返す"""
        for key, label in CATEGORIES:
            if key == self.category:
                return label
        return self.category

    @property
    def payment_type_label(self):
        """支払い種別の表示名を返す"""
        for key, label in PAYMENT_TYPES:
            if key == self.payment_type:
                return label
        return self.payment_type
