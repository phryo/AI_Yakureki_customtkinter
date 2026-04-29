import sqlite3
import time
from typing import Optional, List, Tuple

from settings.setting import DB_PATH

class DBOperator:
    def __init__(self, db_path: str = DB_PATH):
        self.db_name = str(db_path)
        self._init_db()
        self.cleanup_old_summaries(days=7)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_name, timeout=10)
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self):
        """データベースを初期化し、テーブルを作成する"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 共有フォルダでは WAL を使わず、通常のジャーナルにする
            cursor.execute("PRAGMA journal_mode=DELETE;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=5000;")  # 5秒待つ（好みで調整）

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
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    transcription TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dictionaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    UNIQUE(name, title)
                );
            """)
            self._ensure_summaries_transcription_column(cursor)
            conn.commit()

    @staticmethod
    def _ensure_summaries_transcription_column(cursor: sqlite3.Cursor) -> None:
        """既存DBに transcription 列が無い場合のみ追加する。"""
        cursor.execute("PRAGMA table_info(summaries);")
        columns = {row[1] for row in cursor.fetchall()}
        if "transcription" not in columns:
            cursor.execute("ALTER TABLE summaries ADD COLUMN transcription TEXT;")

    def _execute_with_retry(self, query: str, params: tuple = (), retries: int = 5, wait: float = 0.2) -> None:
        """
        database is locked が出たら少し待ってリトライする共通メソッド
        """
        for i in range(retries):
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    if i == retries - 1:
                        raise  # リトライ回数オーバーなのでそのまま投げる
                    time.sleep(wait)
                else:
                    raise

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
        self._execute_with_retry(
            "INSERT INTO names (name) VALUES (?);",
            (name,)
        )

    def load_names_list(self) -> list[str]:
        """名前一覧を新しい順で取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM names ORDER BY created_at ASC;"
            )
            rows = cursor.fetchall()
        return [row[0] for row in rows]

    def delete_name(self, name: str) -> None:
        """名前の削除"""
        retries: int = 5
        wait: float = 0.2
        for i in range(retries):
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM names WHERE name = ?;",
                        (name,)
                    )
                    cursor.execute(
                        "DELETE FROM dictionaries WHERE name = ?;",
                        (name,)
                    )
                    conn.commit()
                    return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    if i == retries - 1:
                        raise
                    time.sleep(wait)
                else:
                    raise

    def rename_name(self, old_name: str, new_name: str) -> None:
        """名前を変更し、過去要約の name も同時に更新する"""
        retries: int = 5
        wait: float = 0.2
        for i in range(retries):
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE names SET name = ? WHERE name = ?;",
                        (new_name, old_name)
                    )
                    cursor.execute(
                        "UPDATE summaries SET name = ? WHERE name = ?;",
                        (new_name, old_name)
                    )
                    cursor.execute(
                        "UPDATE dictionaries SET name = ? WHERE name = ?;",
                        (new_name, old_name)
                    )
                    conn.commit()
                    return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    if i == retries - 1:
                        raise
                    time.sleep(wait)
                else:
                    raise

    # === 要約の操作 ===
    def save_summary(
        self,
        content: str,
        name: Optional[str],
        memo: Optional[str],
        transcription: Optional[str] = None,
    ) -> int:
        """要約を保存し、作成されたIDを返す"""
        retries: int = 5
        wait: float = 0.2
        for i in range(retries):
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO summaries (name, memo, content, transcription) VALUES (?, ?, ?, ?);",
                        (name, memo, content, transcription)
                    )
                    conn.commit()
                    return int(cursor.lastrowid)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    if i == retries - 1:
                        raise
                    time.sleep(wait)
                else:
                    raise

    def load_summary(self, target_date: Optional[str] = None, name: Optional[str] = None) -> List[Tuple]:
        """
        要約のリストを取得
        :param target_date:'YYYY-MM-DD' 形式の文字列。Noneなら日付条件なし
        :param name: 名前で絞り込みたい場合の文字列。Noneなら名前条件なし。
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            base_query = """
                SELECT id, name, memo, content, created_at, transcription
                FROM summaries
            """

            conditions = []
            params: list = []

            # 日付条件
            if target_date:
                conditions.append("date(created_at) = date(?)")
                params.append(target_date)

            # 名前条件
            if name:
                conditions.append("name = ?")
                params.append(name)

            if conditions:
                query = base_query + " WHERE " + " AND ".join(conditions)
            else:
                query = base_query
            query += " ORDER BY created_at DESC;"

            cursor.execute(query, params)
            rows = cursor.fetchall()
        return rows

    def load_dictionaries(self, name: Optional[str] = None) -> List[Tuple]:
        """辞書のリストを取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            base_query = """
                SELECT id, name, title, content, created_at
                FROM dictionaries
            """
            params: list = []

            if name:
                query = base_query + " WHERE name = ?"
                params.append(name)
            else:
                query = base_query

            query += " ORDER BY created_at DESC, id DESC;"
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return rows

    def save_dictionary(self, name: Optional[str], title: str, content: str) -> int:
        """辞書を保存し、作成されたIDを返す"""
        retries: int = 5
        wait: float = 0.2
        for i in range(retries):
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO dictionaries (name, title, content) VALUES (?, ?, ?);",
                        (name, title, content)
                    )
                    conn.commit()
                    return int(cursor.lastrowid)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    if i == retries - 1:
                        raise
                    time.sleep(wait)
                else:
                    raise

    def overwrite_save_dictionary(self, dictionary_id: int, name: Optional[str], title: str, content: str) -> None:
        """辞書を更新して保存"""
        self._execute_with_retry(
            "UPDATE dictionaries SET name = ?, title = ?, content = ? WHERE id = ?;",
            (name, title, content, dictionary_id)
        )

    def delete_dictionary(self, dictionary_id: int) -> None:
        """辞書を削除"""
        self._execute_with_retry(
            "DELETE FROM dictionaries WHERE id = ?;",
            (dictionary_id,)
        )

    def dictionary_title_exists(
        self,
        name: Optional[str],
        title: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """同一名義内に同名タイトルの辞書があるかを返す"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT 1
                FROM dictionaries
                WHERE name = ? AND title = ?
            """
            params: list = [name, title]
            if exclude_id is not None:
                query += " AND id != ?"
                params.append(exclude_id)
            query += " LIMIT 1;"
            cursor.execute(query, params)
            row = cursor.fetchone()
        return row is not None

    def overwrite_save_summary(self, summary_id, content: str) -> None:
        """修正した後の要約を更新して保存"""
        self._execute_with_retry(
            "UPDATE summaries SET content = ? where id = ?;",
            (content, summary_id)
        )
