"""
查询引擎模块
提供数据库查询、表头信息查看和数据检索功能
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import json

class QueryEngine:
    """查询引擎 - 支持灵活的数据查询"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_table_info(self, table_id: int) -> Optional[Dict[str, Any]]:
        """获取表的基本信息和表头"""
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
            'data_source_id': table.data_source_id,
            'description': table.description,
            'columns': [{
                'id': col.id,
                'name': col.column_name,
                'display_name': col.display_name,
                'data_type': col.data_type,
                'column_order': col.column_order,
                'is_required': col.is_required,
                'description': col.description
            } for col in columns],
            'created_at': table.created_at.isoformat(),
            'updated_at': table.updated_at.isoformat()
        }
    
    def get_table_headers(self, table_id: int) -> List[Dict[str, Any]]:
        """获取表的表头信息（字段列表）"""
        from database.schema import TableColumn
        
        columns = self.session.query(TableColumn).filter(
            TableColumn.table_id == table_id
        ).order_by(TableColumn.column_order).all()
        
        return [{
            'id': col.id,
            'name': col.column_name,
            'display_name': col.display_name,
            'data_type': col.data_type,
            'order': col.column_order
        } for col in columns]
    
    def get_all_tables(self, data_source_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取所有动态表列表"""
        from database.schema import DynamicTable
        
        query = self.session.query(DynamicTable)
        
        if data_source_id:
            query = query.filter(DynamicTable.data_source_id == data_source_id)
        
        tables = query.all()
        
        return [{
            'id': table.id,
            'table_name': table.table_name,
            'display_name': table.display_name,
            'data_source_id': table.data_source_id,
            'description': table.description,
            'record_count': self._get_table_record_count(table.id)
        } for table in tables]
    
    def _get_table_record_count(self, table_id: int) -> int:
        """获取表的记录数量"""
        from database.schema import TableDataRecord
        
        return self.session.query(TableDataRecord).filter(
            TableDataRecord.table_id == table_id
        ).count()
    
    def query_table(self, table_id: int, 
                    filters: Optional[Dict[str, Any]] = None,
                    pagination: Optional[Dict[str, int]] = None,
                    sort: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        查询表数据
        
        参数:
            table_id: 表ID
            filters: 过滤条件，如 {'column_name': 'value'} 或 {'column_name': {'operator': 'like', 'value': '%test%'}}
            pagination: 分页参数，如 {'page': 1, 'page_size': 20}
            sort: 排序参数，如 {'column': 'name', 'direction': 'asc'}
        
        返回:
            查询结果和分页信息
        """
        from database.schema import TableDataRecord, TableColumn
        
        # 获取表结构
        table_info = self.get_table_info(table_id)
        if not table_info:
            return {'error': '表不存在'}
        
        columns = table_info['columns']
        column_names = [col['name'] for col in columns]
        
        # 构建查询
        query = self.session.query(TableDataRecord).filter(
            TableDataRecord.table_id == table_id
        )
        
        # 应用过滤条件
        if filters:
            filter_conditions = self._build_filter_conditions(filters, column_names)
            if filter_conditions:
                query = query.filter(or_(*filter_conditions))
        
        # 获取总记录数
        total_count = query.count()
        
        # 应用排序
        if sort and 'column' in sort and sort['column'] in column_names:
            sort_column = getattr(TableDataRecord.data, sort['column'])
            if sort.get('direction', 'asc') == 'desc':
                sort_column = sort_column.desc()
            query = query.order_by(sort_column)
        else:
            # 默认按ID排序
            query = query.order_by(TableDataRecord.id)
        
        # 应用分页
        page = pagination.get('page', 1) if pagination else 1
        page_size = pagination.get('page_size', 20) if pagination else 20
        offset = (page - 1) * page_size
        
        query = query.offset(offset).limit(page_size)
        
        # 执行查询
        records = query.all()
        
        # 转换数据格式
        data = []
        for record in records:
            record_data = record.data.copy()
            record_data['_id'] = record.id
            record_data['_import_batch'] = record.import_batch
            data.append(record_data)
        
        return {
            'table_id': table_id,
            'table_name': table_info['table_name'],
            'display_name': table_info['display_name'],
            'columns': columns,
            'data': data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size
            },
            'filters_applied': filters,
            'sort_applied': sort
        }
    
    def _build_filter_conditions(self, filters: Dict[str, Any], 
                                  column_names: List[str]) -> List:
        """构建过滤条件"""
        from database.schema import TableDataRecord
        
        conditions = []
        
        for col_name, value in filters.items():
            if col_name not in column_names:
                continue
            
            if isinstance(value, dict):
                # 高级过滤：{'column': {'operator': 'like', 'value': '%test%'}}
                operator = value.get('operator', 'eq')
                filter_value = value.get('value')
            else:
                # 简单过滤：{'column': 'value'}
                operator = 'eq'
                filter_value = value
            
            # 根据操作符构建条件
            json_column = TableDataRecord.data[col_name]
            
            if operator == 'eq':
                conditions.append(json_column == filter_value)
            elif operator == 'ne':
                conditions.append(json_column != filter_value)
            elif operator == 'like':
                conditions.append(json_column.like(f'%{filter_value}%'))
            elif operator == 'ilike':
                conditions.append(json_column.ilike(f'%{filter_value}%'))
            elif operator == 'gt':
                conditions.append(json_column > filter_value)
            elif operator == 'gte':
                conditions.append(json_column >= filter_value)
            elif operator == 'lt':
                conditions.append(json_column < filter_value)
            elif operator == 'lte':
                conditions.append(json_column <= filter_value)
            elif operator == 'in':
                if isinstance(filter_value, list):
                    conditions.append(json_column.in_(filter_value))
            elif operator == 'is_null':
                conditions.append(json_column == None)
            elif operator == 'is_not_null':
                conditions.append(json_column != None)
        
        return conditions
    
    def advanced_query(self, table_id: int, 
                       conditions: List[Dict[str, Any]],
                       logic_operator: str = 'and',
                       pagination: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        高级查询 - 支持复杂的条件组合
        
        参数:
            table_id: 表ID
            conditions: 条件列表，每个条件包含 field, operator, value
            logic_operator: 条件之间的逻辑运算符 ('and' 或 'or')
            pagination: 分页参数
        """
        from database.schema import TableColumn
        
        table_info = self.get_table_info(table_id)
        if not table_info:
            return {'error': '表不存在'}
        
        column_names = [col['name'] for col in table_info['columns']]
        
        # 构建查询
        query = self.session.query(TableDataRecord).filter(
            TableDataRecord.table_id == table_id
        )
        
        # 构建条件
        conditions_list = []
        for cond in conditions:
            field = cond.get('field')
            operator = cond.get('operator', 'eq')
            value = cond.get('value')
            
            if field not in column_names:
                continue
            
            json_column = TableDataRecord.data[field]
            
            if operator == 'eq':
                conditions_list.append(json_column == value)
            elif operator == 'ne':
                conditions_list.append(json_column != value)
            elif operator == 'like':
                conditions_list.append(json_column.like(f'%{value}%'))
            elif operator == 'ilike':
                conditions_list.append(json_column.ilike(f'%{value}%'))
            elif operator == 'gt':
                conditions_list.append(json_column > value)
            elif operator == 'gte':
                conditions_list.append(json_column >= value)
            elif operator == 'lt':
                conditions_list.append(json_column < value)
            elif operator == 'lte':
                conditions_list.append(json_column <= value)
        
        # 应用逻辑运算符
        if conditions_list:
            if logic_operator == 'and':
                query = query.filter(and_(*conditions_list))
            else:
                query = query.filter(or_(*conditions_list))
        
        # 获取总数
        total_count = query.count()
        
        # 分页
        page = pagination.get('page', 1) if pagination else 1
        page_size = pagination.get('page_size', 20) if pagination else 20
        offset = (page - 1) * page_size
        
        query = query.offset(offset).limit(page_size)
        records = query.all()
        
        # 转换数据
        data = []
        for record in records:
            record_data = record.data.copy()
            record_data['_id'] = record.id
            data.append(record_data)
        
        return {
            'table_id': table_id,
            'data': data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size
            }
        }
    
    def search_all_tables(self, search_term: str, 
                          data_source_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        全文搜索 - 在所有表中搜索指定内容
        
        返回包含搜索结果的表列表
        """
        from database.schema import TableDataRecord, DynamicTable
        
        tables = self.get_all_tables(data_source_id)
        results = []
        
        for table in tables:
            # 在每个表中搜索
            search_results = self._search_in_table(table['id'], search_term)
            if search_results['count'] > 0:
                results.append({
                    'table_id': table['id'],
                    'table_name': table['table_name'],
                    'display_name': table['display_name'],
                    'matching_records': search_results['count'],
                    'sample_data': search_results['sample'][:3]  # 只返回前3条
                })
        
        return results
    
    def _search_in_table(self, table_id: int, search_term: str) -> Dict[str, Any]:
        """在单个表中搜索"""
        from database.schema import TableDataRecord
        
        # 获取表的所有列
        table_info = self.get_table_info(table_id)
        if not table_info:
            return {'count': 0, 'sample': []}
        
        column_names = [col['name'] for col in table_info['columns']]
        
        # 构建搜索条件
        search_conditions = []
        for col_name in column_names:
            json_column = TableDataRecord.data[col_name]
            search_conditions.append(json_column.ilike(f'%{search_term}%'))
        
        query = self.session.query(TableDataRecord).filter(
            TableDataRecord.table_id == table_id
        ).filter(or_(*search_conditions))
        
        count = query.count()
        records = query.limit(10).all()
        
        sample = []
        for record in records:
            record_data = record.data.copy()
            record_data['_id'] = record.id
            sample.append(record_data)
        
        return {'count': count, 'sample': sample}
    
    def get_data_source_info(self, data_source_id: int) -> Optional[Dict[str, Any]]:
        """获取数据源的详细信息"""
        from database.schema import DataSource, DynamicTable, ImportLog
        
        data_source = self.session.query(DataSource).get(data_source_id)
        if not data_source:
            return None
        
        tables = self.get_all_tables(data_source_id)
        
        # 获取最近导入记录
        recent_imports = self.session.query(ImportLog).filter(
            ImportLog.data_source_id == data_source_id
        ).order_by(ImportLog.imported_at.desc()).limit(5).all()
        
        return {
            'id': data_source.id,
            'name': data_source.name,
            'source_file': data_source.source_file,
            'description': data_source.description,
            'created_by_id': data_source.created_by_id,
            'created_at': data_source.created_at.isoformat(),
            'updated_at': data_source.updated_at.isoformat(),
            'tables_count': len(tables),
            'tables': tables,
            'recent_imports': [{
                'id': imp.id,
                'file_name': imp.file_name,
                'sheet_name': imp.sheet_name,
                'rows_imported': imp.rows_imported,
                'status': imp.status,
                'imported_at': imp.imported_at.isoformat()
            } for imp in recent_imports]
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        from database.schema import DataSource, DynamicTable, TableDataRecord, User
        
        data_sources_count = self.session.query(DataSource).count()
        tables_count = self.session.query(DynamicTable).count()
        records_count = self.session.query(TableDataRecord).count()
        users_count = self.session.query(User).count()
        
        # 获取各表记录分布
        table_stats = self.session.query(
            DynamicTable.table_name,
            DynamicTable.display_name,
            TableDataRecord.table_id,
        ).join(TableDataRecord).group_by(TableDataRecord.table_id).all()
        
        table_distribution = [{
            'table_name': stat[0],
            'display_name': stat[1],
            'table_id': stat[2],
            'count': self.session.query(TableDataRecord).filter(
                TableDataRecord.table_id == stat[2]
            ).count()
        } for stat in table_stats]
        
        return {
            'data_sources': data_sources_count,
            'tables': tables_count,
            'records': records_count,
            'users': users_count,
            'table_distribution': table_distribution
        }
