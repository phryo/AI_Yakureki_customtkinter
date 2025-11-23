import sqlite3
from typing import Optional, List, Tuple

from settings.setting import DB_NAME

class DBOperator:
    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name
        self._init_db()
        self.cleanup_old_summaries(days=7)

    def _get_connection(self):
        return sqlite3.connect(self.db_name, timeout=10)

    def _init_db(self):
        """データベースを初期化し、テーブルを作成する"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS names (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    memo TEXT,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );
            """)
            conn.commit()

    def cleanup_old_summaries(self, days: int = 7) -> None:
        """
        古い要約を削除する。
        :param days: 何日前より前のデータを消すか（デフォルト7日）
        :return: None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # created_at が 「今のローカル時間 - days 日」よりも古いものを削除
            cursor.execute(
                f"""
                DELETE FROM summaries
                WHERE created_at < datetime('now', 'localtime', '-{days} days');
                """
            )
            conn.commit()

    # === 投薬者の操作 ===
    def add_name(self, name: str) -> None:
        """名前を追加"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO names (name) VALUES (?);",
                (name,)
            )
            conn.commit()

    def load_names_list(self) -> list[str]:
        """名前一覧を新しい順で取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM names ORDER BY created_at DESC;"
            )
            rows = cursor.fetchall()
        return [row[0] for row in rows]

    def delete_name(self, name: str) -> None:
        """名前の削除"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM names WHERE name = ?;",
                (name,)
            )
            conn.commit()

    # === 要約の操作 ===
    def save_summary(self, content: str, name: Optional[str], memo: Optional[str]) -> None:
        """要約を保存"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO summaries (name, memo, content) VALUES (?, ?, ?);",
                (name, memo, content)
            )
            conn.commit()

    def load_summary(self, target_date: Optional[str] = None) -> List[Tuple]:
        """
        要約のリストを取得
        :param target_date:'YYYY-MM-DD' 形式の文字列。Noneなら
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if target_date:
                cursor.execute(
                    """
                    SELECT id, name, memo, content, created_at
                    FROM summaries 
                    WHERE date(created_at) = date(?) 
                    order by created_at DESC;
                    """,
                    (target_date,)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, name, memo, content, created_at
                    FROM summaries
                    ORDER BY created_at DESC;
                    """
                )

            rows = cursor.fetchall()
        return rows