"""
Google スプレッドシート データベース操作モジュール
"""

import json
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

# スプレッドシートのカラム定義
COLUMNS = [
    "id",
    "amount",
    "category",
    "memo",
    "date",
    "paid_by",
    "is_settled",
    "created_at",
    "updated_at",
]


@st.cache_resource
def get_client():
    """Google Sheets クライアントを取得（キャッシュ）"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # Streamlit secrets から認証情報を取得
    try:
        creds_dict = st.secrets["gcp_service_account"]
        if isinstance(creds_dict, str):
            creds_dict = json.loads(creds_dict)
        else:
            creds_dict = dict(creds_dict)
    except Exception as e:
        st.error(f"認証情報の読み込みに失敗しました: {e}")
        st.stop()

    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)


def get_spreadsheet():
    """スプレッドシートを取得"""
    client = get_client()
    spreadsheet_url = st.secrets.get("SPREADSHEET_URL")
    if spreadsheet_url:
        return client.open_by_url(spreadsheet_url)
    else:
        spreadsheet_key = st.secrets.get("SPREADSHEET_KEY")
        return client.open_by_key(spreadsheet_key)


def get_worksheet():
    """ワークシートを取得"""
    spreadsheet = get_spreadsheet()
    try:
        return spreadsheet.worksheet("expenses")
    except gspread.WorksheetNotFound:
        # 新規作成
        worksheet = spreadsheet.add_worksheet(title="expenses", rows=1000, cols=10)
        worksheet.append_row(COLUMNS)
        return worksheet


def init_database():
    """データベース（スプレッドシート）を初期化"""
    worksheet = get_worksheet()
    # ヘッダー行の確認
    try:
        first_row = worksheet.row_values(1)
        if first_row != COLUMNS:
            worksheet.update("A1", [COLUMNS])
    except Exception:
        worksheet.update("A1", [COLUMNS])


def _get_next_id(worksheet) -> int:
    """次のIDを取得"""
    all_values = worksheet.get_all_values()
    if len(all_values) <= 1:
        return 1
    ids = []
    for row in all_values[1:]:
        if row and row[0]:
            try:
                ids.append(int(row[0]))
            except ValueError:
                pass
    return max(ids, default=0) + 1


def _row_to_dict(row: list) -> dict:
    """行データを辞書に変換"""
    if len(row) < len(COLUMNS):
        row = row + [""] * (len(COLUMNS) - len(row))
    data = dict(zip(COLUMNS, row))
    # 型変換
    data["id"] = int(data["id"]) if data["id"] else 0
    data["amount"] = int(data["amount"]) if data["amount"] else 0
    data["is_settled"] = bool(int(data["is_settled"])) if data["is_settled"] else False
    return data


def add_expense(
    amount: int,
    category: str,
    memo: str,
    date: str,
    paid_by: str,
) -> int:
    """支出を追加"""
    worksheet = get_worksheet()
    now = datetime.now().isoformat()
    new_id = _get_next_id(worksheet)

    row = [
        new_id,      # id
        amount,      # amount
        category,    # category
        memo,        # memo
        date,        # date
        paid_by,     # paid_by
        0,           # is_settled
        now,         # created_at
        now,         # updated_at
    ]
    worksheet.append_row(row, value_input_option="USER_ENTERED")
    return new_id


def get_all_expenses() -> list[dict]:
    """全ての支出を取得"""
    worksheet = get_worksheet()
    all_values = worksheet.get_all_values()

    if len(all_values) <= 1:
        return []

    expenses = [_row_to_dict(row) for row in all_values[1:] if row and row[0]]
    # 日付とIDで降順ソート
    expenses.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    return expenses


def get_expenses_by_month(year: int, month: int) -> list[dict]:
    """指定月の支出を取得"""
    date_prefix = f"{year:04d}-{month:02d}"
    all_expenses = get_all_expenses()
    return [e for e in all_expenses if e["date"].startswith(date_prefix)]


def get_unsettled_expenses() -> list[dict]:
    """未清算の支出を取得"""
    all_expenses = get_all_expenses()
    return [e for e in all_expenses if not e["is_settled"]]


def _find_row_by_id(worksheet, expense_id: int) -> Optional[int]:
    """IDから行番号を検索（1-indexed）"""
    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values[1:], start=2):
        if row and row[0]:
            try:
                if int(row[0]) == expense_id:
                    return i
            except ValueError:
                pass
    return None


def update_expense(
    expense_id: int,
    amount: Optional[int] = None,
    category: Optional[str] = None,
    memo: Optional[str] = None,
    date: Optional[str] = None,
    paid_by: Optional[str] = None,
) -> bool:
    """支出を更新"""
    worksheet = get_worksheet()
    row_num = _find_row_by_id(worksheet, expense_id)
    if not row_num:
        return False

    existing_row = worksheet.row_values(row_num)
    existing = _row_to_dict(existing_row)

    now = datetime.now().isoformat()
    updated_row = [
        expense_id,
        amount if amount is not None else existing["amount"],
        category if category is not None else existing["category"],
        memo if memo is not None else existing["memo"],
        date if date is not None else existing["date"],
        paid_by if paid_by is not None else existing["paid_by"],
        1 if existing["is_settled"] else 0,
        existing["created_at"],
        now,
    ]
    worksheet.update(f"A{row_num}", [updated_row], value_input_option="USER_ENTERED")
    return True


def toggle_settled(expense_id: int) -> bool:
    """清算済みステータスをトグル"""
    worksheet = get_worksheet()
    row_num = _find_row_by_id(worksheet, expense_id)
    if not row_num:
        return False

    existing_row = worksheet.row_values(row_num)
    existing = _row_to_dict(existing_row)

    new_status = 0 if existing["is_settled"] else 1
    now = datetime.now().isoformat()

    # is_settled (G列) と updated_at (I列) を更新
    worksheet.update(f"G{row_num}", [[new_status]], value_input_option="USER_ENTERED")
    worksheet.update(f"I{row_num}", [[now]], value_input_option="USER_ENTERED")
    return True


def delete_expense(expense_id: int) -> bool:
    """支出を削除"""
    worksheet = get_worksheet()
    row_num = _find_row_by_id(worksheet, expense_id)
    if not row_num:
        return False

    worksheet.delete_rows(row_num)
    return True


def calculate_balance(expenses: list[dict], users: list[str]) -> dict:
    """残高を計算"""
    if len(users) != 2:
        raise ValueError("ユーザーは2人である必要があります")

    user_a, user_b = users

    user_totals = {user_a: 0, user_b: 0}
    for expense in expenses:
        if not expense["is_settled"]:
            paid_by = expense["paid_by"]
            if paid_by in user_totals:
                user_totals[paid_by] += expense["amount"]

    total = sum(user_totals.values())
    share = total // 2
    balance_a = user_totals[user_a] - share

    if balance_a > 0:
        return {
            "user_totals": user_totals,
            "total": total,
            "share": share,
            "balance": balance_a,
            "debtor": user_b,
            "creditor": user_a,
        }
    elif balance_a < 0:
        return {
            "user_totals": user_totals,
            "total": total,
            "share": share,
            "balance": abs(balance_a),
            "debtor": user_a,
            "creditor": user_b,
        }
    else:
        return {
            "user_totals": user_totals,
            "total": total,
            "share": share,
            "balance": 0,
            "debtor": None,
            "creditor": None,
        }


def get_monthly_summary(year: int, month: int, users: list[str]) -> dict:
    """月別サマリーを取得"""
    expenses = get_expenses_by_month(year, month)

    category_totals = {}
    for expense in expenses:
        cat = expense["category"]
        category_totals[cat] = category_totals.get(cat, 0) + expense["amount"]

    user_totals = {user: 0 for user in users}
    for expense in expenses:
        paid_by = expense["paid_by"]
        if paid_by in user_totals:
            user_totals[paid_by] += expense["amount"]

    total = sum(expense["amount"] for expense in expenses)

    return {
        "year": year,
        "month": month,
        "total": total,
        "category_totals": category_totals,
        "user_totals": user_totals,
        "expense_count": len(expenses),
    }
