"""数据库初始化脚本"""
from sqlalchemy import text
from app.db.database import engine
from app.db.models import Base


def init_db():
    """创建所有表"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def setup_pgvector():
    """安装 pgvector 扩展"""
    print("Setting up pgvector extension...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    print("pgvector extension installed successfully!")


if __name__ == "__main__":
    setup_pgvector()
    init_db()
