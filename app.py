"""
同棲カップル向け家計簿アプリ（スマホ対応版）
"""

import streamlit as st
from datetime import datetime, date
import pandas as pd

from config import USERS, CATEGORIES
from database import (
    init_database,
    add_expense,
    get_all_expenses,
    get_expenses_by_month,
    get_unsettled_expenses,
    update_expense,
    delete_expense,
    toggle_settled,
    calculate_balance,
    get_monthly_summary,
)

# ページ設定（スマホ向けにcentered）
st.set_page_config(
    page_title="ふたりの家計簿",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# スマホ向けCSS
st.markdown("""
<style>
    /* 全体のパディング調整 */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    /* ボタンを大きく */
    .stButton > button {
        width: 100%;
        padding: 0.75rem 1rem;
        font-size: 1.1rem;
    }

    /* カード風スタイル */
    .expense-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border-left: 4px solid #4CAF50;
    }

    .expense-card.settled {
        border-left-color: #9e9e9e;
        opacity: 0.7;
    }

    .expense-amount {
        font-size: 1.4rem;
        font-weight: bold;
        color: #1a1a1a;
    }

    .expense-meta {
        color: #666;
        font-size: 0.9rem;
    }

    /* 清算バナー */
    .balance-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.25rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1rem;
    }

    .balance-banner .amount {
        font-size: 1.8rem;
        font-weight: bold;
    }

    /* タブのフォントサイズ */
    .stTabs [data-baseweb="tab"] {
        font-size: 1rem;
        padding: 0.75rem 1rem;
    }

    /* metric調整 */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }

    /* セレクトボックス */
    .stSelectbox {
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# データベース初期化
init_database()


def format_currency(amount: int) -> str:
    """金額をフォーマット"""
    return f"¥{amount:,}"


def render_balance_card():
    """残高表示カード（スマホ最適化）"""
    expenses = get_unsettled_expenses()
    balance_info = calculate_balance(expenses, USERS)

    # メインの清算情報を目立たせる
    if balance_info["balance"] == 0:
        st.success("✅ **精算不要** - 支払いは均等です！", icon="✅")
    else:
        st.markdown(f"""
        <div class="balance-banner">
            <div style="font-size: 0.9rem; margin-bottom: 0.5rem;">💸 清算が必要です</div>
            <div class="amount">{format_currency(balance_info['balance'])}</div>
            <div style="margin-top: 0.5rem;">
                <strong>{balance_info['debtor']}</strong> → <strong>{balance_info['creditor']}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 支払い状況（折りたたみ）
    with st.expander("📊 支払い状況を見る"):
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label=USERS[0],
                value=format_currency(balance_info["user_totals"][USERS[0]]),
            )
        with col2:
            st.metric(
                label=USERS[1],
                value=format_currency(balance_info["user_totals"][USERS[1]]),
            )
        st.caption(f"未清算合計: {format_currency(balance_info['total'])}")


def render_expense_form():
    """支出入力フォーム（スマホ最適化）"""
    st.markdown("### 📝 支出を入力")

    with st.form("expense_form", clear_on_submit=True):
        # 金額を大きく表示
        amount = st.number_input(
            "💴 金額",
            min_value=0,
            step=100,
            format="%d",
            help="支払った金額を入力",
        )

        # 2カラムで支払者と日付
        col1, col2 = st.columns(2)
        with col1:
            paid_by = st.selectbox("👤 支払った人", USERS)
        with col2:
            expense_date = st.date_input("📅 日付", value=date.today())

        # カテゴリとメモ
        category = st.selectbox("📂 カテゴリ", CATEGORIES)
        memo = st.text_input("📝 メモ（任意）", placeholder="例: スーパーで買い物")

        submitted = st.form_submit_button("✅ 登録する", use_container_width=True, type="primary")

        if submitted:
            if amount <= 0:
                st.error("金額を入力してください")
            else:
                add_expense(
                    amount=amount,
                    category=category,
                    memo=memo,
                    date=expense_date.isoformat(),
                    paid_by=paid_by,
                )
                st.success("登録しました！")
                st.rerun()


def render_expense_list():
    """支出一覧（スマホ最適化・カード形式）"""
    st.markdown("### 📋 支出一覧")

    # フィルター（折りたたみ）
    with st.expander("🔍 絞り込み"):
        filter_month_options = ["すべて"]
        today = date.today()
        for i in range(12):
            year = today.year if today.month - i > 0 else today.year - 1
            month = today.month - i if today.month - i > 0 else 12 + (today.month - i)
            filter_month_options.append(f"{year}年{month}月")

        filter_month = st.selectbox("月", filter_month_options, key="filter_month")

        col1, col2 = st.columns(2)
        with col1:
            filter_user = st.selectbox("支払者", ["すべて"] + USERS, key="filter_user")
        with col2:
            filter_settled = st.selectbox(
                "清算状況",
                ["すべて", "未清算のみ", "清算済みのみ"],
                key="filter_settled",
            )

        filter_category = st.selectbox(
            "カテゴリ",
            ["すべて"] + CATEGORIES,
            key="filter_category",
        )

    # データ取得
    if filter_month != "すべて":
        year = int(filter_month.split("年")[0])
        month = int(filter_month.split("年")[1].replace("月", ""))
        expenses = get_expenses_by_month(year, month)
    else:
        expenses = get_all_expenses()

    # フィルタ適用
    if filter_category != "すべて":
        expenses = [e for e in expenses if e["category"] == filter_category]
    if filter_user != "すべて":
        expenses = [e for e in expenses if e["paid_by"] == filter_user]
    if filter_settled == "未清算のみ":
        expenses = [e for e in expenses if not e["is_settled"]]
    elif filter_settled == "清算済みのみ":
        expenses = [e for e in expenses if e["is_settled"]]

    if not expenses:
        st.info("該当する支出がありません")
        return

    st.caption(f"{len(expenses)} 件の支出")

    # 編集モード管理
    if "edit_id" not in st.session_state:
        st.session_state.edit_id = None

    for expense in expenses:
        is_editing = st.session_state.edit_id == expense["id"]
        is_settled = expense["is_settled"]

        if is_editing:
            # 編集モード
            with st.container():
                st.markdown("#### ✏️ 編集中")
                with st.form(f"edit_form_{expense['id']}"):
                    edit_amount = st.number_input(
                        "金額",
                        value=expense["amount"],
                        min_value=0,
                        step=100,
                        key=f"edit_amount_{expense['id']}",
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        edit_paid_by = st.selectbox(
                            "支払者",
                            USERS,
                            index=USERS.index(expense["paid_by"]),
                            key=f"edit_paid_{expense['id']}",
                        )
                    with col2:
                        edit_date = st.date_input(
                            "日付",
                            value=datetime.fromisoformat(expense["date"]).date(),
                            key=f"edit_date_{expense['id']}",
                        )

                    edit_category = st.selectbox(
                        "カテゴリ",
                        CATEGORIES,
                        index=CATEGORIES.index(expense["category"]) if expense["category"] in CATEGORIES else 0,
                        key=f"edit_cat_{expense['id']}",
                    )

                    edit_memo = st.text_input(
                        "メモ",
                        value=expense["memo"] or "",
                        key=f"edit_memo_{expense['id']}",
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 保存", use_container_width=True, type="primary"):
                            update_expense(
                                expense["id"],
                                amount=edit_amount,
                                category=edit_category,
                                memo=edit_memo,
                                date=edit_date.isoformat(),
                                paid_by=edit_paid_by,
                            )
                            st.session_state.edit_id = None
                            st.rerun()
                    with col2:
                        if st.form_submit_button("❌ キャンセル", use_container_width=True):
                            st.session_state.edit_id = None
                            st.rerun()
                st.divider()
        else:
            # カード形式で表示
            settled_class = "settled" if is_settled else ""
            settled_icon = "✅" if is_settled else ""

            with st.container():
                # カード上部：金額と基本情報
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{format_currency(expense['amount'])}** {settled_icon}")
                    st.caption(f"{expense['category']} • {expense['paid_by']} • {expense['date']}")
                    if expense["memo"]:
                        st.caption(f"📝 {expense['memo']}")

                with col2:
                    # アクションボタン（縦並び）
                    if st.button("✅" if not is_settled else "↩️", key=f"settle_{expense['id']}", help="清算切替"):
                        toggle_settled(expense["id"])
                        st.rerun()

                # 編集・削除ボタン（小さく）
                col1, col2, col3 = st.columns([2, 1, 1])
                with col2:
                    if st.button("✏️", key=f"edit_{expense['id']}", help="編集"):
                        st.session_state.edit_id = expense["id"]
                        st.rerun()
                with col3:
                    if st.button("🗑️", key=f"del_{expense['id']}", help="削除"):
                        delete_expense(expense["id"])
                        st.rerun()

                st.divider()


def render_monthly_summary():
    """月別サマリー（スマホ最適化）"""
    st.markdown("### 📊 月別サマリー")

    # 月選択
    today = date.today()
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox(
            "年",
            list(range(today.year - 2, today.year + 2)),
            index=2,
            key="summary_year",
        )
    with col2:
        selected_month = st.selectbox(
            "月",
            list(range(1, 13)),
            index=today.month - 1,
            key="summary_month",
        )

    summary = get_monthly_summary(selected_year, selected_month, USERS)

    # 概要（縦並び）
    st.metric("💰 合計支出", format_currency(summary["total"]))

    col1, col2 = st.columns(2)
    with col1:
        st.metric("📝 件数", f"{summary['expense_count']} 件")
    with col2:
        st.metric("👤 1人あたり", format_currency(summary["total"] // 2 if summary["total"] > 0 else 0))

    # ユーザー別支出
    st.markdown("#### 👥 支払者別")
    for user in USERS:
        amount = summary["user_totals"].get(user, 0)
        st.progress(
            amount / summary["total"] if summary["total"] > 0 else 0,
            text=f"{user}: {format_currency(amount)}"
        )

    # カテゴリ別支出
    st.markdown("#### 📂 カテゴリ別")
    if summary["category_totals"]:
        # 金額順にソート
        sorted_cats = sorted(
            summary["category_totals"].items(),
            key=lambda x: x[1],
            reverse=True
        )

        for cat, amount in sorted_cats:
            st.progress(
                amount / summary["total"] if summary["total"] > 0 else 0,
                text=f"{cat}: {format_currency(amount)}"
            )
    else:
        st.info("この月の支出データがありません")


def render_bulk_settle():
    """一括清算機能（スマホ最適化）"""
    st.markdown("### 🔄 清算管理")

    unsettled = get_unsettled_expenses()

    if not unsettled:
        st.success("✅ 未清算の項目はありません")
        return

    st.warning(f"📋 未清算: **{len(unsettled)} 件**")

    # 一括清算ボタン
    if st.button("✅ すべて清算済みにする", type="primary", use_container_width=True):
        for expense in unsettled:
            toggle_settled(expense["id"])
        st.success("すべての項目を清算済みにしました")
        st.rerun()

    st.divider()

    # 未清算一覧
    st.markdown("#### 未清算の支出")
    for expense in unsettled:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{format_currency(expense['amount'])}**")
                st.caption(f"{expense['category']} • {expense['paid_by']} • {expense['date']}")
            with col2:
                if st.button("✅", key=f"settle_tab_{expense['id']}"):
                    toggle_settled(expense["id"])
                    st.rerun()
            st.divider()


def main():
    st.title("💰 ふたりの家計簿")
    st.caption(f"{USERS[0]} & {USERS[1]}")

    # 残高表示（常に表示）
    render_balance_card()

    # タブで画面切り替え
    tab1, tab2, tab3 = st.tabs(["📝 入力", "📋 一覧", "📊 集計"])

    with tab1:
        render_expense_form()

    with tab2:
        render_expense_list()

    with tab3:
        render_monthly_summary()
        st.divider()
        render_bulk_settle()


if __name__ == "__main__":
    main()
