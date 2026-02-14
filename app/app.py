# -*- coding: utf-8 -*-
"""
app.py - カップル家計簿 Web アプリケーション

Flask アプリケーションのメインモジュール。
ルーティング、清算ロジック、CRUD 操作を定義します。
"""

import os
from datetime import date, datetime
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
try:
    # Gunicorn (パッケージとしてインポート: app.app)
    from app.models import db, Transaction, USERS, CATEGORIES, PAYMENT_TYPES
except ImportError:
    # ローカル実行 (python app/app.py)
    from models import db, Transaction, USERS, CATEGORIES, PAYMENT_TYPES


# ========================================
# アプリケーション生成
# ========================================

def create_app():
    """Flask アプリケーションファクトリ"""
    app = Flask(__name__)

    # --- 設定 ---
    basedir = os.path.abspath(os.path.dirname(__file__))

    # DATABASE_URL 環境変数があれば PostgreSQL、なければ SQLite (ローカル開発用)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Render/Heroku は postgres:// を返すが、SQLAlchemy は postgresql:// が必要
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    else:
        instance_dir = os.path.join(basedir, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        db_path = os.path.join(instance_dir, "household.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # --- DB 初期化 ---
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # --- テンプレートにグローバル変数を渡す ---
    @app.context_processor
    def inject_constants():
        return dict(
            users=USERS,
            categories=CATEGORIES,
            payment_types=PAYMENT_TYPES,
            today=date.today().isoformat(),
        )

    # ========================================
    # ルート定義
    # ========================================

    @app.route("/")
    def dashboard():
        """ダッシュボード — 清算結果とサマリを表示"""
        balance = _calculate_balance()
        recent = (
            Transaction.query
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .limit(5)
            .all()
        )
        category_summary = _category_summary()
        monthly_summary = _monthly_summary()
        return render_template(
            "dashboard.html",
            balance=balance,
            recent=recent,
            category_summary=category_summary,
            monthly_summary=monthly_summary,
        )

    @app.route("/add", methods=["GET", "POST"])
    def add_transaction():
        """支出を新規登録"""
        if request.method == "POST":
            try:
                txn = Transaction(
                    date=datetime.strptime(request.form["date"], "%Y-%m-%d").date(),
                    title=request.form["title"].strip(),
                    amount=int(request.form["amount"]),
                    payer=request.form["payer"],
                    category=request.form["category"],
                    payment_type=request.form["payment_type"],
                )
                # バリデーション
                if not txn.title:
                    flash("品目を入力してください。", "danger")
                    return render_template("add_transaction.html", txn=txn)
                if txn.amount <= 0:
                    flash("金額は1円以上で入力してください。", "danger")
                    return render_template("add_transaction.html", txn=txn)

                db.session.add(txn)
                db.session.commit()
                flash("支出を登録しました！", "success")
                return redirect(url_for("dashboard"))
            except (ValueError, KeyError) as e:
                flash(f"入力内容にエラーがあります: {e}", "danger")

        return render_template("add_transaction.html", txn=None)

    @app.route("/edit/<int:txn_id>", methods=["GET", "POST"])
    def edit_transaction(txn_id):
        """支出を編集"""
        txn = Transaction.query.get_or_404(txn_id)

        if request.method == "POST":
            try:
                txn.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
                txn.title = request.form["title"].strip()
                txn.amount = int(request.form["amount"])
                txn.payer = request.form["payer"]
                txn.category = request.form["category"]
                txn.payment_type = request.form["payment_type"]

                if not txn.title:
                    flash("品目を入力してください。", "danger")
                    return render_template("edit_transaction.html", txn=txn)
                if txn.amount <= 0:
                    flash("金額は1円以上で入力してください。", "danger")
                    return render_template("edit_transaction.html", txn=txn)

                db.session.commit()
                flash("支出を更新しました！", "success")
                return redirect(url_for("history"))
            except (ValueError, KeyError) as e:
                flash(f"入力内容にエラーがあります: {e}", "danger")

        return render_template("edit_transaction.html", txn=txn)

    @app.route("/delete/<int:txn_id>", methods=["POST"])
    def delete_transaction(txn_id):
        """支出を削除"""
        txn = Transaction.query.get_or_404(txn_id)
        db.session.delete(txn)
        db.session.commit()
        flash("支出を削除しました。", "info")
        return redirect(url_for("history"))

    @app.route("/history")
    def history():
        """全履歴一覧"""
        page = request.args.get("page", 1, type=int)
        per_page = 20
        pagination = (
            Transaction.query
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )
        return render_template("history.html", pagination=pagination)

    # ========================================
    # ヘルパー関数
    # ========================================

    def _calculate_balance():
        """
        清算バランスを計算する。

        計算式:
        balance = (A が B のために払った額 + A が払った割り勘の半額)
                - (B が A のために払った額 + B が払った割り勘の半額)

        balance > 0 → B が A に balance 円支払う
        balance < 0 → A が B に |balance| 円支払う
        balance == 0 → 清算不要
        """
        user_a, user_b = USERS[0], USERS[1]
        transactions = Transaction.query.all()

        # A が B のために払った額 (A が payer で payment_type='partner')
        a_paid_for_b = sum(
            t.amount for t in transactions
            if t.payer == user_a and t.payment_type == "partner"
        )
        # A が払った割り勘の半額
        a_split_half = sum(
            t.amount for t in transactions
            if t.payer == user_a and t.payment_type == "split"
        ) / 2

        # B が A のために払った額
        b_paid_for_a = sum(
            t.amount for t in transactions
            if t.payer == user_b and t.payment_type == "partner"
        )
        # B が払った割り勘の半額
        b_split_half = sum(
            t.amount for t in transactions
            if t.payer == user_b and t.payment_type == "split"
        ) / 2

        balance = (a_paid_for_b + a_split_half) - (b_paid_for_a + b_split_half)

        return {
            "value": int(balance),
            "abs_value": abs(int(balance)),
            "user_a": user_a,
            "user_b": user_b,
            "a_paid_for_b": int(a_paid_for_b),
            "a_split_half": int(a_split_half),
            "b_paid_for_a": int(b_paid_for_a),
            "b_split_half": int(b_split_half),
            "a_total": int(a_paid_for_b + a_split_half),
            "b_total": int(b_paid_for_a + b_split_half),
        }

    def _category_summary():
        """カテゴリ別の支出合計を返す"""
        transactions = Transaction.query.all()
        summary = {}
        for t in transactions:
            label = t.category_label
            summary[label] = summary.get(label, 0) + t.amount
        # 金額降順でソート
        return sorted(summary.items(), key=lambda x: x[1], reverse=True)

    def _monthly_summary():
        """今月の支出合計を返す"""
        today = date.today()
        first_day = today.replace(day=1)
        transactions = (
            Transaction.query
            .filter(Transaction.date >= first_day)
            .all()
        )
        total = sum(t.amount for t in transactions)
        count = len(transactions)
        return {"total": total, "count": count, "month": today.strftime("%Y年%m月")}

    return app


# ========================================
# エントリポイント
# ========================================

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
