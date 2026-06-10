import os
import logging
import aiosqlite
import asyncpg
from config import DB_NAME

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = DB_NAME):
        self.db_path = db_path
        self.db_url = os.getenv("DATABASE_URL")
        
        # Render sometimes provides DATABASE_URL starting with postgres://
        # but asyncpg requires postgresql://
        if self.db_url and self.db_url.startswith("postgres://"):
            self.db_url = self.db_url.replace("postgres://", "postgresql://", 1)
            
        self.is_postgres = bool(self.db_url)
        if self.is_postgres:
            logger.info("Database: Running in PostgreSQL mode.")
        else:
            logger.info(f"Database: Running in SQLite mode ({self.db_path}).")

    async def init_db(self):
        """Initializes the database, creating required tables if they don't exist."""
        if self.is_postgres:
            conn = await asyncpg.connect(self.db_url)
            try:
                # Table for Users
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Table for Movies
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS movies (
                        id SERIAL PRIMARY KEY,
                        code TEXT UNIQUE,
                        title TEXT NOT NULL,
                        description TEXT,
                        genre TEXT,
                        file_id TEXT NOT NULL,
                        file_type TEXT DEFAULT 'video',
                        views INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            finally:
                await conn.close()
        else:
            async with aiosqlite.connect(self.db_path) as db:
                # Table for Users
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Table for Movies
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS movies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code TEXT UNIQUE,
                        title TEXT NOT NULL,
                        description TEXT,
                        genre TEXT,
                        file_id TEXT NOT NULL,
                        file_type TEXT DEFAULT 'video',
                        views INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.commit()

    async def _execute(self, query: str, *args):
        """Executes a write query (INSERT, UPDATE, DELETE) and commits."""
        if self.is_postgres:
            query = self._convert_query(query)
            conn = await asyncpg.connect(self.db_url)
            try:
                await conn.execute(query, *args)
            finally:
                await conn.close()
        else:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(query, args)
                await db.commit()

    async def _fetch_all(self, query: str, *args) -> list:
        """Executes a select query and returns list of dicts."""
        if self.is_postgres:
            query = self._convert_query(query)
            conn = await asyncpg.connect(self.db_url)
            try:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
            finally:
                await conn.close()
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, args) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]

    async def _fetch_one(self, query: str, *args) -> dict:
        """Executes a select query and returns a single dict (or None)."""
        if self.is_postgres:
            query = self._convert_query(query)
            conn = await asyncpg.connect(self.db_url)
            try:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
            finally:
                await conn.close()
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, args) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None

    def _convert_query(self, query: str) -> str:
        """Converts query from SQLite syntax to PostgreSQL syntax."""
        # Translate parameter placeholders: ? -> $1, $2, etc.
        count = 1
        while '?' in query:
            query = query.replace('?', f'${count}', 1)
            count += 1
        # Use ILIKE for case-insensitive matches in Postgres
        query = query.replace(" LIKE ", " ILIKE ")
        return query

    # User Management
    async def add_user(self, user_id: int, username: str, first_name: str):
        """Adds a new user to the database or updates their info if already exists."""
        query = """
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name
        """
        await self._execute(query, user_id, username, first_name)

    async def get_user_count(self) -> int:
        """Returns total number of registered users."""
        row = await self._fetch_one("SELECT COUNT(*) as count FROM users")
        return row['count'] if row else 0

    async def get_all_users(self) -> list:
        """Returns all user IDs."""
        rows = await self._fetch_all("SELECT user_id FROM users")
        return [row['user_id'] for row in rows]

    # Movie Management
    async def add_movie(self, code: str, title: str, description: str, file_id: str, file_type: str = "video", genre: str = "Boshqa") -> bool:
        """Adds a new movie to the database. Returns True if successful, False if code exists."""
        query = """
            INSERT INTO movies (code, title, description, file_id, file_type, genre)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            await self._execute(query, code, title, description, file_id, file_type, genre)
            return True
        except Exception as e:
            logger.error(f"Error adding movie: {e}")
            return False

    async def get_movie_by_code(self, code: str) -> dict:
        """Retrieves a movie details by its user-facing code."""
        return await self._fetch_one("SELECT * FROM movies WHERE code = ?", code)

    async def search_movies(self, query: str) -> list:
        """Searches movies by title or description matching query."""
        return await self._fetch_all(
            "SELECT * FROM movies WHERE title LIKE ? OR description LIKE ? OR genre LIKE ? LIMIT 10",
            f"%{query}%", f"%{query}%", f"%{query}%"
        )

    async def delete_movie_by_code(self, code: str) -> bool:
        """Deletes a movie by its code. Returns True if deleted, False otherwise."""
        exists = await self._fetch_one("SELECT 1 as exists FROM movies WHERE code = ?", code)
        if not exists:
            return False
        await self._execute("DELETE FROM movies WHERE code = ?", code)
        return True

    async def get_movies_count(self) -> int:
        """Returns total number of movies."""
        row = await self._fetch_one("SELECT COUNT(*) as count FROM movies")
        return row['count'] if row else 0

    async def increment_views(self, code: str):
        """Increments movie views/downloads counter."""
        await self._execute("UPDATE movies SET views = views + 1 WHERE code = ?", code)

    async def get_top_movies(self, limit: int = 10) -> list:
        """Returns movies sorted by most views."""
        return await self._fetch_all("SELECT * FROM movies ORDER BY views DESC LIMIT ?", limit)

    async def get_next_movie_code(self) -> str:
        """Determines the next numeric movie code in sequence. Starts at 100."""
        rows = await self._fetch_all("SELECT code FROM movies")
        max_code = 99  # Starts at 100
        for row in rows:
            code_str = row['code']
            if code_str.isdigit():
                max_code = max(max_code, int(code_str))
        return str(max_code + 1)

    async def update_movie_description(self, code: str, description: str) -> bool:
        """Updates the description of a movie by its code. Returns True if updated."""
        exists = await self._fetch_one("SELECT 1 as exists FROM movies WHERE code = ?", code)
        if not exists:
            return False
        await self._execute("UPDATE movies SET description = ? WHERE code = ?", description, code)
        return True

    async def get_total_views(self) -> int:
        """Returns the sum of views for all movies."""
        row = await self._fetch_one("SELECT SUM(views) as total_views FROM movies")
        return row['total_views'] if row and row['total_views'] is not None else 0

    async def get_users_list(self) -> list:
        """Returns all users with details (id, username, first_name, joined_at)."""
        return await self._fetch_all("SELECT user_id, username, first_name, joined_at FROM users")
