import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BASE_DIR / "movies.db"


def init_database():
    connection = sqlite3.connect(DATABASE_FILE)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                score REAL NOT NULL,
                year INTEGER NOT NULL,
                type TEXT NOT NULL,
                description TEXT
            )
            """
        )

        connection.commit()

    except sqlite3.Error as error:
        connection.rollback()
        print(f"初始化数据库失败：{error}")
        raise

    finally:
        connection.close()

    print("数据库初始化完成")


def add_movie(movie):
    connection = sqlite3.connect(DATABASE_FILE)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO movies (
                name,
                score,
                year,
                type
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                movie["name"],
                movie["score"],
                movie["year"],
                movie["type"],
            ),
        )

        connection.commit()

        return cursor.lastrowid

    except sqlite3.Error as error:
        connection.rollback()
        print(f"添加电影失败：{error}")
        raise

    finally:
        connection.close()


def get_all_movies():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, name, score, year, type
            FROM movies
            ORDER BY id
            """
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    except sqlite3.Error as error:
        print(f"查询全部电影失败：{error}")
        raise

    finally:
        connection.close()


def get_movie_by_id(movie_id: int):
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, name, score, year, type
            FROM movies
            WHERE id = ?
            """,
            (movie_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    except sqlite3.Error as error:
        print(f"根据 ID 查询电影失败：{error}")
        raise

    finally:
        connection.close()


def get_movies_page(
    page: int,
    page_size: int,
):
    offset = (page - 1) * page_size

    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, name, score, year, type
            FROM movies
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            (
                page_size,
                offset,
            ),
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    except sqlite3.Error as error:
        print(f"分页查询电影失败：{error}")
        raise

    finally:
        connection.close()


def get_movie_count():
    connection = sqlite3.connect(DATABASE_FILE)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM movies
            """
        )

        row = cursor.fetchone()

        return row[0]

    except sqlite3.Error as error:
        print(f"查询电影总数失败：{error}")
        raise

    finally:
        connection.close()


def update_movie(
    movie_id: int,
    movie_data: dict,
):
    connection = sqlite3.connect(DATABASE_FILE)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE movies
            SET
                name = ?,
                score = ?,
                year = ?,
                type = ?
            WHERE id = ?
            """,
            (
                movie_data["name"],
                movie_data["score"],
                movie_data["year"],
                movie_data["type"],
                movie_id,
            ),
        )

        connection.commit()

        affected_rows = cursor.rowcount

        if affected_rows == 0:
            return None

        return get_movie_by_id(movie_id)

    except sqlite3.Error as error:
        connection.rollback()
        print(f"更新电影失败：{error}")
        raise

    finally:
        connection.close()


def partial_update_movie(
    movie_id: int,
    update_data: dict,
):
    if not update_data:
        return None

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        cursor = connection.cursor()

        fields = []
        values = []

        for key, value in update_data.items():
            fields.append(f"{key} = ?")
            values.append(value)

        sql = f"""
        UPDATE movies
        SET {", ".join(fields)}
        WHERE id = ?
        """

        values.append(movie_id)

        cursor.execute(
            sql,
            values,
        )

        connection.commit()

        affected_rows = cursor.rowcount

        if affected_rows == 0:
            return None

        return get_movie_by_id(movie_id)

    except sqlite3.Error as error:
        connection.rollback()
        print(f"部分更新电影失败：{error}")
        raise

    finally:
        connection.close()


def delete_movie(movie_id: int):
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, name, score, year, type
            FROM movies
            WHERE id = ?
            """,
            (movie_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        movie = dict(row)

        cursor.execute(
            """
            DELETE FROM movies
            WHERE id = ?
            """,
            (movie_id,),
        )

        connection.commit()

        return movie

    except sqlite3.Error as error:
        connection.rollback()
        print(f"删除电影失败：{error}")
        raise

    finally:
        connection.close()


def search_movies_db(keyword: str):
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()

        search_keyword = f"%{keyword}%"

        cursor.execute(
            """
            SELECT id, name, score, year, type
            FROM movies
            WHERE name LIKE ?
               OR type LIKE ?
            ORDER BY id
            """,
            (
                search_keyword,
                search_keyword,
            ),
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    except sqlite3.Error as error:
        print(f"搜索电影失败：{error}")
        raise

    finally:
        connection.close()


def filter_movies_db(
    keyword: str | None = None,
    min_score: float | None = None,
    year: int | None = None,
):
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()

        sql = """
        SELECT id, name, score, year, type
        FROM movies
        """

        conditions = []
        values = []

        if keyword is not None:
            conditions.append(
                "(name LIKE ? OR type LIKE ?)"
            )

            search_keyword = f"%{keyword}%"

            values.append(search_keyword)
            values.append(search_keyword)

        if min_score is not None:
            conditions.append(
                "score >= ?"
            )
            values.append(min_score)

        if year is not None:
            conditions.append(
                "year = ?"
            )
            values.append(year)

        if conditions:
            sql += (
                " WHERE "
                + " AND ".join(conditions)
            )

        sql += " ORDER BY id"

        cursor.execute(
            sql,
            values,
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    except sqlite3.Error as error:
        print(f"筛选电影失败：{error}")
        raise

    finally:
        connection.close()


def show_tables():
    connection = sqlite3.connect(DATABASE_FILE)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        )

        tables = cursor.fetchall()

        print(
            "当前数据库中的表：",
            tables,
        )

    except sqlite3.Error as error:
        print(f"查看数据表失败：{error}")
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    init_database()

    movies = get_movies_page(
        page=1,
        page_size=2,
    )

    print(movies)