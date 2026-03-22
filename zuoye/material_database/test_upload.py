#!/usr/bin/env python3
"""
测试Excel上传和导入功能
"""

import sys
import os
import pandas as pd
from datetime import datetime

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'database'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

# 创建测试Excel文件
def create_test_excel():
    """创建一个测试Excel文件"""
    test_file = 'test_data.xlsx'
    
    # 创建示例数据
    data = {
        '材料名称': ['铝合金', '钢铁', '铜合金'],
        '密度': [2.7, 7.85, 8.9],
        '熔点': [933, 1538, 1358],
        '创建日期': [datetime.now(), datetime.now(), datetime.now()]
    }
    
    df = pd.DataFrame(data)
    df.to_excel(test_file, index=False, sheet_name='材料数据')
    
    print(f"✓ 测试Excel文件已创建: {test_file}")
    return test_file

def test_import():
    """测试导入功能"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database.schema import Base, User, DataSource
    from modules.excel_importer import ExcelImporter
    
    # 创建测试Excel文件
    test_file = create_test_excel()
    
    # 连接数据库
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'material_database.db')
    engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 获取或创建测试用户
        test_user = session.query(User).filter(User.username == 'admin').first()
        if not test_user:
            print("❌ 找不到admin用户，请先初始化数据库")
            return False
        
        # 创建测试数据源
        test_source = DataSource(
            name='测试数据源',
            description='用于测试的数据源',
            source_file=test_file,
            created_by_id=test_user.id
        )
        session.add(test_source)
        session.commit()
        print(f"✓ 测试数据源已创建: ID={test_source.id}")
        
        # 测试导入
        excel_importer = ExcelImporter(session)
        result = excel_importer.import_excel_file(test_file, test_source.id, test_user.id)
        
        if 'error' in result:
            print(f"❌ 导入失败: {result['error']}")
            return False
        
        print(f"✓ 导入成功!")
        print(f"  - 处理的sheet数: {result['sheets_imported']}")
        print(f"  - 导入的记录数: {result['total_records']}")
        print(f"  - 详情: {result['details']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"✓ 测试文件已清理")

if __name__ == '__main__':
    print("开始测试Excel导入功能...\n")
    success = test_import()
    sys.exit(0 if success else 1)
