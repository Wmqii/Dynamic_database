"""
Excel数据导入模块
支持读取Excel文件的多个子文件（sheet），并动态导入到数据库
"""

import pandas as pd
import uuid
import re
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
import openpyxl

class ExcelImporter:
    """Excel文件导入器"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_excel_sheets(self, file_path: str) -> List[str]:
        """获取Excel文件的所有子文件（sheet）名称"""
        try:
            xl = pd.ExcelFile(file_path)
            return xl.sheet_names
        except Exception as e:
            raise Exception(f"无法读取Excel文件: {e}")
    
    def read_sheet_data(self, file_path: str, sheet_name: str) -> pd.DataFrame:
        """读取指定sheet的数据"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            return df
        except Exception as e:
            raise Exception(f"无法读取sheet '{sheet_name}': {e}")
    
    def sanitize_column_name(self, name: str) -> str:
        """清理列名，转换为合法的数据库字段名"""
        # 移除特殊字符，只保留字母、数字、下划线
        sanitized = re.sub(r'[^\w]', '_', str(name))
        # 去除连续的多个下划线
        sanitized = re.sub(r'_+', '_', sanitized)
        # 去除首尾下划线
        sanitized = sanitized.strip('_')
        # 如果为空，使用默认名称
        if not sanitized:
            sanitized = f'column_{uuid.uuid4().hex[:8]}'
        return sanitized
    
    def detect_data_type(self, series: pd.Series) -> str:
        """检测列的数据类型"""
        # 移除NaN值
        non_null = series.dropna()
        if len(non_null) == 0:
            return 'TEXT'
        
        # 尝试检测数值类型
        try:
            non_null.astype(float)
            # 检查是否全是整数
            if all(non_null.apply(lambda x: x == int(x) if isinstance(x, float) else True)):
                return 'INTEGER'
            return 'FLOAT'
        except:
            pass
        
        # 检查日期类型
        try:
            pd.to_datetime(non_null)
            return 'DATETIME'
        except:
            pass
        
        return 'TEXT'
    
    def import_sheet_to_table(self, file_path: str, sheet_name: str, 
                               table_name: str, display_name: str,
                               data_source_id: int, user_id: int) -> Tuple[int, str]:
        """
        将Excel的sheet导入到动态表
        
        返回: (导入行数, 状态消息)
        """
        from database.schema import DynamicTable, TableColumn, TableDataRecord, ImportLog
        
        # 读取数据
        df = self.read_sheet_data(file_path, sheet_name)
        
        if df.empty:
            return 0, "Sheet为空，未导入数据"
        
        # 获取或创建动态表
        table = self.session.query(DynamicTable).filter(
            DynamicTable.data_source_id == data_source_id,
            DynamicTable.sheet_index == self._get_sheet_index(file_path, sheet_name)
        ).first()
        
        if not table:
            # 创建新表
            table = DynamicTable(
                data_source_id=data_source_id,
                table_name=table_name,
                display_name=display_name,
                sheet_index=self._get_sheet_index(file_path, sheet_name),
                description=f"从Excel导入: {sheet_name}"
            )
            self.session.add(table)
            self.session.flush()
        
        # 删除旧数据（如果需要重新导入）
        self.session.query(TableDataRecord).filter(TableDataRecord.table_id == table.id).delete()
        self.session.query(TableColumn).filter(TableColumn.table_id == table.id).delete()
        
        # 导入列定义
        columns_info = []
        for idx, col_name in enumerate(df.columns):
            sanitized_name = self.sanitize_column_name(col_name)
            data_type = self.detect_data_type(df[col_name])
            
            column = TableColumn(
                table_id=table.id,
                column_name=sanitized_name,
                display_name=str(col_name),
                data_type=data_type,
                column_order=idx,
                description=f"原始列名: {col_name}"
            )
            self.session.add(column)
            columns_info.append((sanitized_name, str(col_name)))
        
        # 导入数据记录
        import_batch = str(uuid.uuid4())[:8]
        records_count = 0
        
        for _, row in df.iterrows():
            record_data = {}
            for col_sanitized, col_original in columns_info:
                value = row[col_original]
                # 处理NaN和特殊值
                if pd.isna(value):
                    record_data[col_sanitized] = None
                elif isinstance(value, (pd.Timestamp, datetime)):
                    record_data[col_sanitized] = value.isoformat()
                else:
                    record_data[col_sanitized] = value
            
            record = TableDataRecord(
                table_id=table.id,
                data=record_data,
                import_batch=import_batch
            )
            self.session.add(record)
            records_count += 1
        
        self.session.commit()
        
        return records_count, f"成功导入 {records_count} 条记录"
    
    def _get_sheet_index(self, file_path: str, sheet_name: str) -> int:
        """获取sheet在文件中的索引位置"""
        xl = pd.ExcelFile(file_path)
        try:
            return xl.sheet_names.index(sheet_name)
        except:
            return 0
    
    def import_excel_file(self, file_path: str, data_source_id: int, user_id: int) -> Dict[str, Any]:
        """
        导入整个Excel文件的所有sheet
        
        返回: 导入结果汇总
        """
        from database.schema import DataSource, ImportLog
        
        results = {
            'file_path': file_path,
            'sheets_imported': 0,
            'total_records': 0,
            'details': []
        }
        
        try:
            # 验证文件是否存在
            if not os.path.exists(file_path):
                raise Exception(f"文件不存在: {file_path}")
            
            sheets = self.get_excel_sheets(file_path)
            if not sheets:
                raise Exception("Excel文件中没有找到任何sheet")
            
            file_name = os.path.basename(file_path)
            
            for sheet_name in sheets:
                try:
                    # 生成表名
                    table_name = f"tbl_{self.sanitize_column_name(sheet_name)}"
                    
                    rows_imported, message = self.import_sheet_to_table(
                        file_path=file_path,
                        sheet_name=sheet_name,
                        table_name=table_name,
                        display_name=sheet_name,
                        data_source_id=data_source_id,
                        user_id=user_id
                    )
                    
                    results['sheets_imported'] += 1
                    results['total_records'] += rows_imported
                    results['details'].append({
                        'sheet_name': sheet_name,
                        'table_name': table_name,
                        'rows_imported': rows_imported,
                        'status': 'success' if rows_imported > 0 else 'warning'
                    })
                except Exception as sheet_error:
                    results['details'].append({
                        'sheet_name': sheet_name,
                        'status': 'error',
                        'error': str(sheet_error)
                    })
            
            if results['sheets_imported'] == 0:
                raise Exception("没有成功导入任何sheet")
            
            # 记录导入日志
            log = ImportLog(
                data_source_id=data_source_id,
                file_name=file_name,
                status='success',
                rows_imported=results['total_records'],
                imported_by_id=user_id
            )
            self.session.add(log)
            self.session.commit()
            
        except Exception as e:
            results['error'] = str(e)
            self.session.rollback()
        
        return results

class DynamicTableManager:
    """动态表管理器 - 用于管理动态创建的表"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_table_from_template(self, data_source_id: int, 
                                    table_name: str, display_name: str,
                                    columns: List[Dict[str, Any]]) -> int:
        """从模板创建动态表"""
        from database.schema import DynamicTable, TableColumn
        
        # 检查是否已存在
        existing = self.session.query(DynamicTable).filter(
            DynamicTable.data_source_id == data_source_id,
            DynamicTable.table_name == table_name
        ).first()
        
        if existing:
            return existing.id
        
        table = DynamicTable(
            data_source_id=data_source_id,
            table_name=table_name,
            display_name=display_name,
            description=f"手动创建的表: {display_name}"
        )
        self.session.add(table)
        self.session.flush()
        
        for idx, col in enumerate(columns):
            column = TableColumn(
                table_id=table.id,
                column_name=col['name'],
                display_name=col.get('display_name', col['name']),
                data_type=col.get('type', 'TEXT'),
                column_order=idx,
                is_required=col.get('required', False),
                default_value=col.get('default')
            )
            self.session.add(column)
        
        self.session.commit()
        return table.id
    
    def add_column(self, table_id: int, column_info: Dict[str, Any]) -> bool:
        """为动态表添加新列"""
        from database.schema import TableColumn
        
        max_order = self.session.query(TableColumn.column_order).filter(
            TableColumn.table_id == table_id
        ).order_by(TableColumn.column_order.desc()).first()
        
        new_order = (max_order[0] + 1) if max_order else 0
        
        column = TableColumn(
            table_id=table_id,
            column_name=column_info['name'],
            display_name=column_info.get('display_name', column_info['name']),
            data_type=column_info.get('type', 'TEXT'),
            column_order=new_order,
            is_required=column_info.get('required', False),
            description=column_info.get('description')
        )
        
        self.session.add(column)
        self.session.commit()
        return True
    
    def get_table_schema(self, table_id: int) -> Dict[str, Any]:
        """获取表的完整结构信息"""
        from database.schema import DynamicTable, TableColumn
        
        table = self.session.query(DynamicTable).get(table_id)
        if not table:
            return None
        
        columns = self.session.query(TableColumn).filter(
            TableColumn.table_id == table_id
        ).order_by(TableColumn.column_order).all()
        
        return {
            'id': table.id,
            'table_name': table.table_name,
            'display_name': table.display_name,
            'columns': [{
                'id': col.id,
                'name': col.column_name,
                'display_name': col.display_name,
                'type': col.data_type,
                'order': col.column_order,
                'required': col.is_required
            } for col in columns]
        }
