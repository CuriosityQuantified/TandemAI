"""
Migration Runner Script
Executes SQL migration files against PostgreSQL database
"""
import asyncio
import os
from pathlib import Path
import psycopg


async def run_migration(migration_file: str):
    """Execute a SQL migration file"""
    # Get database URI from environment
    db_uri = os.getenv("POSTGRES_URI", "postgresql://localhost:5432/langgraph_checkpoints")

    # Read migration file
    migration_path = Path(__file__).parent / migration_file
    if not migration_path.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_path}")

    migration_sql = migration_path.read_text()

    print(f"🔄 Running migration: {migration_file}")
    print(f"📁 File: {migration_path}")
    print(f"🗄️  Database: {db_uri}")
    print("-" * 60)

    # Execute migration
    try:
        async with await psycopg.AsyncConnection.connect(db_uri) as conn:
            async with conn.cursor() as cur:
                await cur.execute(migration_sql)
                await conn.commit()
                print("✅ Migration executed successfully!")

                # Verify table creation
                await cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'user_threads'
                """)
                result = await cur.fetchone()

                if result:
                    print(f"✅ Verified: user_threads table exists")

                    # Count migrated threads
                    await cur.execute("SELECT COUNT(*) FROM user_threads")
                    count = await cur.fetchone()
                    print(f"📊 Migrated {count[0]} existing thread(s)")
                else:
                    print("⚠️ Warning: user_threads table not found after migration")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    import sys

    # Default migration file
    migration_file = "migrations/003_user_threads.sql"

    # Allow specifying migration file via command line
    if len(sys.argv) > 1:
        migration_file = sys.argv[1]

    asyncio.run(run_migration(migration_file))
