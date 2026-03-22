"""
数据库初始化脚本
包含默认管理员账户创建和基础数据初始化
"""

from schema import create_database, User
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
import os
import sys

# 添加父目录到 Python 路径
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def init_database(db_path='material_database.db'):
    """初始化数据库并创建默认用户"""
    
    # 创建数据库
    engine = create_database(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 检查是否已有用户
        existing_users = session.query(User).count()
        if existing_users > 0:
            print(f"数据库已存在 {existing_users} 个用户，跳过初始化")
            return session
        
        # 创建超级管理员
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            email='admin@material.local',
            user_type='super_admin',
            is_active=True
        )
        
        # 创建普通管理员
        manager = User(
            username='manager',
            password_hash=generate_password_hash('manager123'),
            email='manager@material.local',
            user_type='admin',
            is_active=True
        )
        
        # 创建测试用户
        viewer = User(
            username='viewer',
            password_hash=generate_password_hash('viewer123'),
            email='viewer@material.local',
            user_type='normal',
            is_active=True
        )
        
        session.add_all([admin, manager, viewer])
        session.commit()
        
        print("数据库初始化成功！")
        print("默认账户：")
        print("  - 超级管理员: admin / admin123")
        print("  - 管理员: manager / manager123")
        print("  - 普通用户: viewer / viewer123")
        
        return session
        
    except Exception as e:
        session.rollback()
        print(f"初始化失败: {e}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    init_database()
