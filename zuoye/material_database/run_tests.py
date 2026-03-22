#!/usr/bin/env python3
"""
系统功能测试脚本
验证所有主要功能是否正常工作
"""

import sys
import os
import json
import traceback
from datetime import datetime

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'database'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def test(self, name, func):
        """运行单个测试"""
        try:
            print(f"测试: {name}...", end=" ")
            func()
            print("✓ 通过")
            self.passed += 1
        except AssertionError as e:
            print(f"✗ 失败: {e}")
            self.failed += 1
            self.errors.append((name, str(e)))
        except Exception as e:
            print(f"✗ 错误: {e}")
            self.failed += 1
            self.errors.append((name, traceback.format_exc()))
    
    def summary(self):
        """打印测试总结"""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"测试总结: {self.passed}/{total} 通过")
        print(f"{'='*60}")
        
        if self.errors:
            print("\n失败的测试:")
            for name, error in self.errors:
                print(f"\n  ✗ {name}")
                print(f"    {error}")
        
        return self.failed == 0

def test_imports():
    """测试模块导入"""
    import pandas as pd
    import openpyxl
    from sqlalchemy import create_engine
    from database.schema import Base, User, DataSource
    from modules.excel_importer import ExcelImporter
    from modules.query_engine import QueryEngine
    from modules.user_auth import AccessControlService

def test_database_connection():
    """测试数据库连接"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database.schema import Base, User
    
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'material_database.db')
    engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 测试查询
    users = session.query(User).all()
    assert len(users) > 0, "数据库中没有用户"
    
    session.close()

def test_user_authentication():
    """测试用户认证"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database.schema import User
    from modules.user_auth import UserAuthManager
    
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'material_database.db')
    engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    auth_manager = UserAuthManager(session)
    
    # 测试登录
    result = auth_manager.authenticate('admin', 'admin123')
    assert result is not None, "admin用户登录失败"
    assert result['username'] == 'admin', "用户名不匹配"
    
    session.close()

def test_excel_importer():
    """测试Excel导入模块"""
    import pandas as pd
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database.schema import Base, User, DataSource
    from modules.excel_importer import ExcelImporter
    
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'material_database.db')
    engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 创建测试Excel文件
    test_file = 'test_data_temp.xlsx'
    data = {
        '名称': ['测试1', '测试2'],
        '值': [100, 200]
    }
    df = pd.DataFrame(data)
    df.to_excel(test_file, index=False)
    
    try:
        # 测试导入器初始化
        importer = ExcelImporter(session)
        
        # 测试获取sheet列表
        sheets = importer.get_excel_sheets(test_file)
        assert len(sheets) > 0, "无法读取Excel sheet"
        
        # 测试读取数据
        df_read = importer.read_sheet_data(test_file, sheets[0])
        assert len(df_read) == 2, "读取的数据行数不正确"
        
        # 测试列名清理
        sanitized = importer.sanitize_column_name('测试 列 名')
        assert sanitized, "列名清理失败"
        
        # 测试数据类型检测
        dtype = importer.detect_data_type(df_read['值'])
        assert dtype in ['INTEGER', 'FLOAT'], f"数据类型检测失败: {dtype}"
        
    finally:
        session.close()
        if os.path.exists(test_file):
            os.remove(test_file)

def test_query_engine():
    """测试查询引擎"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database.schema import DynamicTable
    from modules.query_engine import QueryEngine
    
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'material_database.db')
    engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        query_engine = QueryEngine(session)
        
        # 获取所有表
        tables = query_engine.get_all_tables()
        assert isinstance(tables, list), "get_all_tables返回类型错误"
        
        # 获取系统统计
        stats = query_engine.get_statistics()
        assert 'data_sources' in stats, "统计信息缺少data_sources"
        assert 'tables' in stats, "统计信息缺少tables"
        assert 'records' in stats, "统计信息缺少records"
        
    finally:
        session.close()

def test_permission_manager():
    """测试权限管理"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from modules.user_auth import PermissionManager
    
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'material_database.db')
    engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        perm_manager = PermissionManager(session)
        
        # 测试获取可访问的数据源
        accessible = perm_manager.get_accessible_data_sources(1)
        assert isinstance(accessible, list), "get_accessible_data_sources返回类型错误"
        
    finally:
        session.close()

def test_file_operations():
    """测试文件操作"""
    import tempfile
    
    # 测试上传目录
    upload_dir = 'uploads'
    assert os.path.exists(upload_dir), "上传目录不存在"
    assert os.path.isdir(upload_dir), "上传目录不是文件夹"
    
    # 测试文件写入
    test_file = os.path.join(upload_dir, 'test_temp.txt')
    with open(test_file, 'w') as f:
        f.write('test')
    
    assert os.path.exists(test_file), "文件写入失败"
    
    # 清理
    os.remove(test_file)

def test_config():
    """测试配置"""
    # 检查数据库文件
    db_path = os.path.join(os.path.dirname(__file__), 'material_database.db')
    assert os.path.exists(db_path), "数据库文件不存在"
    
    # 检查模板目录
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    assert os.path.exists(templates_dir), "模板目录不存在"
    assert os.path.isdir(templates_dir), "模板目录不是文件夹"

def main():
    """运行所有测试"""
    print("="*60)
    print("动态材料数据库系统 - 功能测试")
    print("="*60)
    print()
    
    runner = TestRunner()
    
    # 运行测试
    runner.test("模块导入", test_imports)
    runner.test("配置检查", test_config)
    runner.test("文件操作", test_file_operations)
    runner.test("数据库连接", test_database_connection)
    runner.test("用户认证", test_user_authentication)
    runner.test("Excel导入模块", test_excel_importer)
    runner.test("查询引擎", test_query_engine)
    runner.test("权限管理", test_permission_manager)
    
    # 打印总结
    success = runner.summary()
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
