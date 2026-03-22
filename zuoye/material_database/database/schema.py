"""
动态材料数据库系统 - 数据库架构设计

核心设计思路：
1. 使用元数据表管理动态表结构
2. 用户权限分级管理
3. 灵活的字段定义支持不同用户定制需求
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()

# ==================== 用户权限管理相关表 ====================

class User(Base):
    """用户表 - 存储系统用户信息"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100))
    user_type = Column(String(20), default='normal')  # super_admin, admin, normal
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    permissions = relationship("UserTablePermission", back_populates="user")
    data_sources = relationship("DataSource", back_populates="created_by")

class UserTablePermission(Base):
    """用户对数据源的访问权限表"""
    __tablename__ = 'user_table_permissions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=False)
    can_view_header = Column(Boolean, default=True)  # 查看表头
    can_query = Column(Boolean, default=True)        # 查询数据
    can_import = Column(Boolean, default=False)      # 导入数据
    can_edit_schema = Column(Boolean, default=False) # 修改表结构
    
    user = relationship("User", back_populates="permissions")
    data_source = relationship("DataSource", back_populates="permissions")

# ==================== 数据源管理相关表 ====================

class DataSource(Base):
    """数据源表 - 存储Excel文件信息"""
    __tablename__ = 'data_sources'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)           # 数据源名称
    source_file = Column(String(255))                    # 原始Excel文件路径
    description = Column(Text)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    created_by = relationship("User", back_populates="data_sources")
    permissions = relationship("UserTablePermission", back_populates="data_source")
    dynamic_tables = relationship("DynamicTable", back_populates="data_source")

class DynamicTable(Base):
    """动态表定义 - 每个Excel子文件对应一个动态表"""
    __tablename__ = 'dynamic_tables'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=False)
    table_name = Column(String(100), nullable=False)     # 表名（英文）
    display_name = Column(String(100), nullable=False)   # 显示名称（中文）
    sheet_index = Column(Integer, default=0)             # Excel子文件索引
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    data_source = relationship("DataSource", back_populates="dynamic_tables")
    columns = relationship("TableColumn", back_populates="table", cascade="all, delete-orphan")
    data_records = relationship("TableDataRecord", back_populates="table", cascade="all, delete-orphan")

class TableColumn(Base):
    """表字段定义 - 动态定义每个表的列信息"""
    __tablename__ = 'table_columns'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey('dynamic_tables.id'), nullable=False)
    column_name = Column(String(100), nullable=False)    # 字段名（英文）
    display_name = Column(String(100), nullable=False)   # 显示名称（中文）
    data_type = Column(String(50), default='TEXT')       # 数据类型
    column_order = Column(Integer, default=0)            # 字段顺序
    is_required = Column(Boolean, default=False)         # 是否必填
    default_value = Column(Text)
    description = Column(Text)
    
    table = relationship("DynamicTable", back_populates="columns")

class TableDataRecord(Base):
    """表数据记录 - 存储实际数据（使用JSON存储灵活字段值）"""
    __tablename__ = 'table_data_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey('dynamic_tables.id'), nullable=False)
    data = Column(JSON, nullable=False)                  # 存储为JSON格式的动态数据
    import_batch = Column(String(50))                    # 导入批次号
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    table = relationship("DynamicTable", back_populates="data_records")

class ImportLog(Base):
    """导入日志表 - 记录数据导入历史"""
    __tablename__ = 'import_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'))
    file_name = Column(String(255))
    sheet_name = Column(String(100))
    rows_imported = Column(Integer, default=0)
    status = Column(String(20))  # success, failed, partial
    error_message = Column(Text)
    imported_by_id = Column(Integer, ForeignKey('users.id'))
    imported_at = Column(DateTime, default=datetime.now)

# ==================== 数据库工厂函数 ====================

def create_database(db_path='material_database.db'):
    """创建数据库引擎"""
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    return engine

if __name__ == '__main__':
    # 测试数据库创建
    engine = create_database('test.db')
    print("数据库创建成功！")
