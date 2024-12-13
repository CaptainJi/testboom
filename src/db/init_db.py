from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .base import Base
from .models import *  # 导入所有模型

# 创建数据库引擎
engine = create_engine('sqlite:///testboom.db')

def init_db():
    """初始化数据库"""
    # 创建所有表
    Base.metadata.create_all(engine)
    
    # 创建会话工厂
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return SessionLocal()

if __name__ == '__main__':
    print("正在初始化数据库...")
    init_db()
    print("数据库初始化完成!") 