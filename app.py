"""
同棲カップル向け家計簿アプリ
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

# ページ設定
st.set_page_config(
    page_title="ふたりの家計簿",
    page_icon="💰",
    layout="wide",
)

# データベース初期化
init_database()


def format_currency(amount: int) -> str:
    """金額をフォーマット"""
    return f"¥{amount:,}"


def render_balance_card():
    """残高表示カード"""
    expenses = get_unsettled_expenses()
    balance_info = calculate_balance(expenses, USERS)

    st.markdown("### 💳 清算ステータス")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label=f"{USERS[0]} の支払い総額",
            value=format_currency(balance_info["user_totals"][USERS[0]]),
        )

    with col2:
        st.metric(
            label=f"{USERS[1]} の支払い総額",
            value=format_currency(balance_info["user_totals"][USERS[1]]),
        )

    with col3:
        if balance_info["balance"] == 0:
            st.success("✅ 精算不要（均等です）")
        else:
            st.warning(
                f"💸 **{balance_info['debtor']}** さんが "
                f"**{balance_info['creditor']}** さんに "
                f"**{format_currency(balance_info['balance'])}** 支払う必要があります"
            )


def render_expense_form():
    """支出入力フォーム"""
    st.markdown("### 📝 支出を入力")

    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            amount = st.number_input(
                "金額",
                min_value=0,
                step=100,
                format="%d",
            )
            category = st.selectbox("カテゴリ", CATEGORIES)
            memo = st.text_input("メモ（任意）")

        with col2:
            expense_date = st.date_input(
                "日付",
                value=date.today(),
            )
            paid_by = st.selectbox("支払った人", USERS)

        submitted = st.form_submit_button("💾 登録", use_container_width=True)

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
    """支出一覧"""
    st.markdown("### 📋 支出一覧")

    # フィルター
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        filter_category = st.selectbox(
            "カテゴリで絞り込み",
            ["すべて"] + CATEGORIES,
            key="filter_category",
        )

    with col2:
        filter_user = st.selectbox(
            "支払者で絞り込み",
            ["すべて"] + USERS,
            key="filter_user",
        )

    with col3:
        filter_settled = st.selectbox(
            "清算状況",
            ["すべて", "未清算のみ", "清算済みのみ"],
            key="filter_settled",
        )

    with col4:
        # 月で絞り込み
        today = date.today()
        months = []
        for i in range(12):
            year = today.year if today.month - i > 0 else today.year - 1
            month = today.month - i if today.month - i > 0 else 12 + (today.month - i)
            months.append(f"{year}年{month}月")
        filter_month = st.selectbox(
            "月で絞り込み",
            ["すべて"] + months,
            key="filter_month",
        )

    # データ取得
    if filter_month != "すべて":
        # 月の解析
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

    # 編集モード管理
    if "edit_id" not in st.session_state:
        st.session_state.edit_id = None

    for expense in expenses:
        is_editing = st.session_state.edit_id == expense["id"]

        with st.container():
            if is_editing:
                # 編集モード
                with st.form(f"edit_form_{expense['id']}"):
                    col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 2])

                    with col1:
                        edit_amount = st.number_input(
                            "金額",
                            value=expense["amount"],
                            min_value=0,
                            step=100,
                            key=f"edit_amount_{expense['id']}",
                        )
                    with col2:
                        edit_category = st.selectbox(
                            "カテゴリ",
                            CATEGORIES,
                            index=CATEGORIES.index(expense["category"]),
                            key=f"edit_cat_{expense['id']}",
                        )
                    with col3:
                        edit_memo = st.text_input(
                            "メモ",
                            value=expense["memo"] or "",
                            key=f"edit_memo_{expense['id']}",
                        )
                    with col4:
                        edit_date = st.date_input(
                            "日付",
                            value=datetime.fromisoformat(expense["date"]).date(),
                            key=f"edit_date_{expense['id']}",
                        )
                    with col5:
                        edit_paid_by = st.selectbox(
                            "支払者",
                            USERS,
                            index=USERS.index(expense["paid_by"]),
                            key=f"edit_paid_{expense['id']}",
                        )
                    with col6:
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("保存"):
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
                        with col_cancel:
                            if st.form_submit_button("キャンセル"):
                                st.session_state.edit_id = None
                                st.rerun()
            else:
                # 表示モード
                settled_mark = "✅" if expense["is_settled"] else "⬜"
                date_str = expense["date"]

                col1, col2, col3, col4, col5, col6, col7 = st.columns(
                    [1, 2, 2, 3, 2, 2, 2]
                )

                with col1:
                    if st.button(
                        settled_mark,
                        key=f"settle_{expense['id']}",
                        help="クリックで清算状況を切り替え",
                    ):
                        toggle_settled(expense["id"])
                        st.rerun()

                with col2:
                    st.write(f"**{format_currency(expense['amount'])}**")

                with col3:
                    st.write(expense["category"])

                with col4:
                    st.write(expense["memo"] or "-")

                with col5:
                    st.write(date_str)

                with col6:
                    st.write(expense["paid_by"])

                with col7:
                    col_edit, col_delete = st.columns(2)
                    with col_edit:
                        if st.button("✏️", key=f"edit_{expense['id']}"):
                            st.session_state.edit_id = expense["id"]
                            st.rerun()
                    with col_delete:
                        if st.button("🗑️", key=f"del_{expense['id']}"):
                            delete_expense(expense["id"])
                            st.rerun()

            st.divider()


def render_monthly_summary():
    """月別サマリー"""
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

    # 概要
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("合計支出", format_currency(summary["total"]))
    with col2:
        st.metric("件数", f"{summary['expense_count']} 件")
    with col3:
        st.metric("1人あたり", format_currency(summary["total"] // 2))

    # ユーザー別支出
    st.markdown("#### 👥 支払者別")
    user_df = pd.DataFrame(
        {
            "支払者": list(summary["user_totals"].keys()),
            "金額": list(summary["user_totals"].values()),
        }
    )
    if not user_df.empty and user_df["金額"].sum() > 0:
        st.bar_chart(user_df.set_index("支払者"))

    # カテゴリ別支出
    st.markdown("#### 📂 カテゴリ別")
    if summary["category_totals"]:
        cat_df = pd.DataFrame(
            {
                "カテゴリ": list(summary["category_totals"].keys()),
                "金額": list(summary["category_totals"].values()),
            }
        ).sort_values("金額", ascending=False)

        st.bar_chart(cat_df.set_index("カテゴリ"))

        # 詳細テーブル
        cat_df["金額"] = cat_df["金額"].apply(format_currency)
        st.dataframe(cat_df, use_container_width=True, hide_index=True)
    else:
        st.info("この月の支出データがありません")


def render_bulk_settle():
    """一括清算機能"""
    st.markdown("### 🔄 一括清算")

    unsettled = get_unsettled_expenses()
    if not unsettled:
        st.success("未清算の項目はありません")
        return

    st.write(f"未清算の項目: {len(unsettled)} 件")

    if st.button("すべて清算済みにする", type="primary"):
        for expense in unsettled:
            toggle_settled(expense["id"])
        st.success("すべての項目を清算済みにしました")
        st.rerun()


def main():
    st.title("💰 ふたりの家計簿")
    st.caption(f"ユーザー: {USERS[0]} & {USERS[1]}")

    # 残高表示（常に表示）
    render_balance_card()

    st.divider()

    # タブで画面切り替え
    tab1, tab2, tab3 = st.tabs(["📝 入力・一覧", "📊 月別サマリー", "⚙️ 清算管理"])

    with tab1:
        render_expense_form()
        st.divider()
        render_expense_list()

    with tab2:
        render_monthly_summary()

    with tab3:
        render_bulk_settle()

        st.divider()

        # 未清算一覧
        st.markdown("#### 未清算の支出")
        unsettled = get_unsettled_expenses()
        if unsettled:
            for expense in unsettled:
                col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 1])
                with col1:
                    st.write(format_currency(expense["amount"]))
                with col2:
                    st.write(expense["category"])
                with col3:
                    st.write(expense["memo"] or "-")
                with col4:
                    st.write(expense["paid_by"])
                with col5:
                    if st.button("✅", key=f"settle_tab_{expense['id']}"):
                        toggle_settled(expense["id"])
                        st.rerun()
        else:
            st.info("未清算の項目はありません")


if __name__ == "__main__":
    main()
