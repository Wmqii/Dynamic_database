"""
动态材料数据库系统 - 主应用程序
提供Web界面和API接口
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from  werkzeug.utils import secure_filename
import os
import sys
import uuid
from datetime import datetime

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'database'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from database.schema import Base, DataSource, DynamicTable, TableColumn, TableDataRecord, User, UserTablePermission, ImportLog
from database.init_db import init_database
from modules.excel_importer import ExcelImporter, DynamicTableManager
from modules.user_auth import AccessControlService
from modules.query_engine import QueryEngine

app = Flask(__name__)
app.secret_key = 'material_database_secret_key_change_in_production'

# 数据库配置 - 使用绝对路径避免Flask instance文件夹问题
DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DATABASE_DIR, 'material_database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# 初始化数据库
with app.app_context():
    init_database(DATABASE_PATH)

access_control = AccessControlService(db.session)
query_engine = QueryEngine(db.session)
excel_importer = ExcelImporter(db.session)
table_manager = DynamicTableManager(db.session)

# ==================== 辅助函数 ====================

def get_current_user():
    """获取当前登录用户"""
    user_id = session.get('user_id')
    if user_id:
        return db.session.query(User).get(user_id)
    return None

def require_login(f):
    """登录验证装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.is_json:
                return jsonify({'error': '请先登录'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def require_permission(permission_type):
    """权限验证装饰器工厂"""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': '请先登录'}), 401
            
            if user.user_type == 'super_admin':
                return f(*args, **kwargs)
            
            data_source_id = kwargs.get('data_source_id')
            if data_source_id:
                has_permission = access_control.permission_manager.check_permission(
                    user.id, data_source_id, permission_type
                )
                if not has_permission:
                    return jsonify({'error': f'没有 {permission_type} 权限'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def export_table_data(result, format_type='csv'):
    """导出表数据"""
    import csv
    import io
    from flask import make_response
    
    if 'error' in result:
        return jsonify({'error': result['error']}), 400
    
    data = result.get('data', [])
    columns = result.get('columns', [])
    table_name = result.get('table_name', 'export')
    
    if format_type == 'csv':
        # 创建CSV文件
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[col['name'] for col in columns])
        writer.writeheader()
        writer.writerows(data)
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename={table_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        return response
    
    elif format_type == 'xlsx':
        # 创建Excel文件
        try:
            import openpyxl
            from openpyxl.utils import get_column_letter
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = table_name[:31]  # Excel sheet名称限制31个字符
            
            # 写入表头
            for col_idx, col in enumerate(columns, 1):
                ws.cell(row=1, column=col_idx, value=col['display_name'])
            
            # 写入数据
            for row_idx, row_data in enumerate(data, 2):
                for col_idx, col in enumerate(columns, 1):
                    value = row_data.get(col['name'], '')
                    ws.cell(row=row_idx, column=col_idx, value=value)
            
            # 调整列宽
            for col_idx, col in enumerate(columns, 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = 15
            
            # 保存到内存
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            response = make_response(output.getvalue())
            response.headers['Content-Disposition'] = f'attachment; filename={table_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            return response
        except ImportError:
            return jsonify({'error': 'openpyxl库未安装，无法导出Excel'}), 500
    
    else:
        return jsonify({'error': f'不支持的导出格式: {format_type}'}), 400

# ==================== 页面路由 ====================

@app.route('/')
def index():
    """首页"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    stats = query_engine.get_statistics()
    return render_template('index.html', user=user, stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        result = access_control.login(username, password)
        
        if result['success']:
            user = db.session.query(User).filter(User.username == username).first()
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_type'] = user.user_type
            
            if request.is_json:
                return jsonify(result)
            return redirect(url_for('index'))
        else:
            if request.is_json:
                return jsonify(result), 401
            return render_template('login.html', error=result.get('error'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        result = access_control.register_user(username, password, email)
        
        if result['success']:
            if request.is_json:
                return jsonify(result)
            return redirect(url_for('login'))
        else:
            if request.is_json:
                return jsonify(result), 400
            return render_template('register.html', error=result.get('error'))
    
    return render_template('register.html')

@app.route('/data-sources')
@require_login
def data_sources():
    """数据源管理页面"""
    user = get_current_user()
    
    if user.user_type == 'super_admin':
        sources = db.session.query(DataSource).all()
    else:
        # 获取用户有权限访问的数据源
        source_ids = [p.data_source_id for p in db.session.query(UserTablePermission).filter(
            UserTablePermission.user_id == user.id
        ).all()]
        sources = db.session.query(DataSource).filter(DataSource.id.in_(source_ids)).all()
    
    return render_template('data_sources.html', user=user, data_sources=sources)

@app.route('/table/<int:table_id>')
@require_login
def view_table(table_id):
    """查看表数据页面"""
    user = get_current_user()
    
    table_info = query_engine.get_table_info(table_id)
    if not table_info:
        return render_template('error.html', error='表不存在')
    
    # 检查权限
    if user.user_type != 'super_admin':
        has_access = False
        for perm in db.session.query(UserTablePermission).filter(
            UserTablePermission.user_id == user.id
        ).all():
            if perm.data_source_id == table_info.get('data_source_id'):
                has_access = True
                break
        if not has_access:
            return render_template('error.html', error='没有访问权限')
    
    return render_template('table_view.html', user=user, table=table_info)

@app.route('/admin')
@require_login
def admin_panel():
    """管理员面板"""
    user = get_current_user()
    
    if user.user_type != 'super_admin':
        return render_template('error.html', error='需要超级管理员权限')
    
    users = db.session.query(User).all()
    sources = db.session.query(DataSource).all()
    stats = query_engine.get_statistics()
    
    return render_template('admin.html', user=user, users=users, data_sources=sources, stats=stats)

@app.route('/admin/users')
@require_login
def admin_users():
    """用户管理页面"""
    user = get_current_user()
    if user.user_type != 'super_admin':
        return render_template('error.html', error='需要超级管理员权限')
    
    users = db.session.query(User).all()
    return render_template('users.html', user=user, users=users)

@app.route('/admin/permissions/<int:data_source_id>')
@require_login
def admin_permissions(data_source_id):
    """权限管理页面"""
    user = get_current_user()
    if user.user_type != 'super_admin':
        return render_template('error.html', error='需要超级管理员权限')
    
    data_source = db.session.query(DataSource).get(data_source_id)
    users = db.session.query(User).all()
    permissions = access_control.permission_manager.get_data_source_permissions(data_source_id)
    
    return render_template('permissions.html', user=user, data_source=data_source, 
                           users=users, permissions=permissions)

# ==================== API 接口 ====================

@app.route('/api/login', methods=['POST'])
def api_login():
    """API登录"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    result = access_control.login(username, password)
    
    if result['success']:
        user = db.session.query(User).filter(User.username == username).first()
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_type'] = user.user_type
    
    return jsonify(result)

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """API登出"""
    session.clear()
    return jsonify({'success': True, 'message': '已退出登录'})

@app.route('/api/current-user')
def api_current_user():
    """获取当前用户信息"""
    user = get_current_user()
    if not user:
        return jsonify({'logged_in': False})
    
    return jsonify({
        'logged_in': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'user_type': user.user_type
        }
    })

@app.route('/api/data-sources', methods=['GET'])
@require_login
def api_data_sources():
    """获取数据源列表"""
    user = get_current_user()
    
    if user.user_type == 'super_admin':
        # 超级管理员可以看到所有数据源
        sources = db.session.query(DataSource).all()
    else:
        # 普通用户可以看到自己创建的数据源和有权限的数据源
        created_sources = db.session.query(DataSource).filter(DataSource.created_by_id == user.id).all()
        
        # 获取有权限的数据源
        from database.schema import UserTablePermission
        permissions = db.session.query(UserTablePermission).filter(
            UserTablePermission.user_id == user.id
        ).all()
        permitted_source_ids = [p.data_source_id for p in permissions]
        permitted_sources = db.session.query(DataSource).filter(
            DataSource.id.in_(permitted_source_ids)
        ).all() if permitted_source_ids else []
        
        # 合并两个列表，去重
        source_ids = set([s.id for s in created_sources] + [s.id for s in permitted_sources])
        sources = db.session.query(DataSource).filter(DataSource.id.in_(source_ids)).all()
    
    return jsonify({
        'data_sources': [{
            'id': s.id,
            'name': s.name,
            'description': s.description,
            'source_file': s.source_file,
            'created_at': s.created_at.isoformat()
        } for s in sources]
    })

@app.route('/api/data-sources', methods=['POST'])
@require_login
def api_create_data_source():
    """创建数据源"""
    user = get_current_user()
    
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': '数据源名称不能为空'}), 400
    
    source = DataSource(
        name=data['name'],
        description=data.get('description', ''),
        source_file='',
        created_by_id=user.id
    )
    
    db.session.add(source)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data_source': {
            'id': source.id,
            'name': source.name,
            'description': source.description
        }
    })

@app.route('/api/data-sources/<int:data_source_id>/tables', methods=['GET'])
@require_login
def api_data_source_tables(data_source_id):
    """获取数据源下的所有表"""
    tables = query_engine.get_all_tables(data_source_id)
    return jsonify({'tables': tables})

@app.route('/api/tables/<int:table_id>', methods=['GET'])
@require_login
def api_table_info(table_id):
    """获取表信息"""
    table = query_engine.get_table_info(table_id)
    if not table:
        return jsonify({'error': '表不存在'}), 404
    
    return jsonify(table)

@app.route('/api/tables/<int:table_id>/headers', methods=['GET'])
@require_login
def api_table_headers(table_id):
    """获取表头信息"""
    headers = query_engine.get_table_headers(table_id)
    return jsonify({'headers': headers})

@app.route('/api/tables/<int:table_id>/data', methods=['GET'])
@require_login
def api_table_data(table_id):
    """查询表数据"""
    user = get_current_user()
    
    try:
        # 检查是否是DataTables请求
        is_datatables = request.args.get('draw') is not None
        
        if is_datatables:
            # DataTables服务器端处理模式
            draw = request.args.get('draw', 1, type=int)
            start = request.args.get('start', 0, type=int)
            length = request.args.get('length', 20, type=int)
            page = (start // length) + 1 if length > 0 else 1
            page_size = length
            
            # 获取排序参数
            sort_column = None
            sort_direction = 'asc'
            if request.args.get('order[0][column]'):
                try:
                    col_index = int(request.args.get('order[0][column]', 0))
                    # 跳过ID列
                    if col_index > 0:
                        sort_direction = request.args.get('order[0][dir]', 'asc')
                except:
                    pass
            
            # 构建过滤参数
            filters = {}
            search_value = request.args.get('search[value]', '')
            if search_value:
                # 全局搜索
                filters['_search'] = search_value
            
            # 构建排序参数
            sort = None
            if sort_column:
                sort = {'column': sort_column, 'direction': sort_direction}
            
            result = query_engine.query_table(
                table_id=table_id,
                filters=filters if filters else None,
                pagination={'page': page, 'page_size': page_size},
                sort=sort
            )
            
            # 返回DataTables格式的响应
            return jsonify({
                'draw': draw,
                'recordsTotal': result.get('pagination', {}).get('total_count', 0),
                'recordsFiltered': result.get('pagination', {}).get('total_count', 0),
                'data': result.get('data', []),
                'error': None
            })
        else:
            # 普通API请求
            page = request.args.get('page', 1, type=int)
            page_size = request.args.get('page_size', 20, type=int)
            sort_column = request.args.get('sort_column')
            sort_direction = request.args.get('sort_direction', 'asc')
            export_format = request.args.get('export', None)
            
            # 构建过滤参数
            filters = {}
            for key in request.args:
                if key.startswith('filter_'):
                    filter_column = key[7:]  # 移除 'filter_' 前缀
                    filters[filter_column] = request.args.get(key)
            
            # 构建排序参数
            sort = None
            if sort_column:
                sort = {'column': sort_column, 'direction': sort_direction}
            
            result = query_engine.query_table(
                table_id=table_id,
                filters=filters if filters else None,
                pagination={'page': page, 'page_size': page_size},
                sort=sort
            )
            
            # 如果请求导出
            if export_format:
                return export_table_data(result, export_format)
            
            return jsonify(result)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        # 检查是否是DataTables请求
        if request.args.get('draw'):
            return jsonify({
                'draw': request.args.get('draw', 1, type=int),
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': [],
                'error': f'查询失败: {str(e)}'
            }), 200  # 返回200以避免DataTables错误
        else:
            return jsonify({
                'error': f'查询失败: {str(e)}',
                'data': [],
                'pagination': {'page': 1, 'page_size': 20, 'total_count': 0, 'total_pages': 0}
            }), 500

@app.route('/api/import', methods=['POST'])
@require_login
def api_import_excel():
    """导入Excel文件"""
    user = get_current_user()
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        # 检查文件扩展名
        filename = secure_filename(file.filename)
        if not filename or not filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': '只支持Excel文件(.xlsx, .xls)'}), 400
        
        # 获取或创建数据源
        data_source_id = request.form.get('data_source_id', type=int)
        if not data_source_id:
            return jsonify({'success': False, 'error': '必须指定数据源ID'}), 400
        
        # 验证数据源是否存在
        data_source = db.session.query(DataSource).get(data_source_id)
        if not data_source:
            return jsonify({'success': False, 'error': '数据源不存在'}), 404
        
        # 确保上传目录存在
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # 保存上传的文件
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{data_source_id}_{uuid.uuid4().hex[:8]}_{filename}')
        file.save(upload_path)
        
        # 验证文件是否成功保存
        if not os.path.exists(upload_path):
            return jsonify({'success': False, 'error': '文件保存失败'}), 500
        
        try:
            # 导入数据
            result = excel_importer.import_excel_file(upload_path, data_source_id, user.id)
            
            # 检查导入是否有错误
            if 'error' in result:
                return jsonify({'success': False, 'error': result['error']}), 400
            
            return jsonify({
                'success': True,
                'result': result
            })
        finally:
            # 清理上传的文件
            if os.path.exists(upload_path):
                try:
                    os.remove(upload_path)
                except:
                    pass
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'导入失败: {str(e)}'
        }), 500

@app.route('/api/search', methods=['GET'])
@require_login
def api_search():
    """全文搜索"""
    query_text = request.args.get('q', '')
    if not query_text:
        return jsonify({'results': []})
    
    data_source_id = request.args.get('data_source_id', type=int)
    results = query_engine.search_all_tables(query_text, data_source_id)
    
    return jsonify({'results': results, 'query': query_text})

@app.route('/api/statistics')
@require_login
def api_statistics():
    """获取数据库统计信息"""
    stats = query_engine.get_statistics()
    return jsonify(stats)

# ==================== 用户管理 API ====================

@app.route('/api/users', methods=['GET'])
@require_login
def api_users():
    """获取用户列表"""
    user = get_current_user()
    if user.user_type != 'super_admin':
        return jsonify({'error': '需要超级管理员权限'}), 403
    
    users = db.session.query(User).all()
    return jsonify({
        'users': [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'user_type': u.user_type,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat()
        } for u in users]
    })

@app.route('/api/users', methods=['POST'])
@require_login
def api_create_user():
    """创建用户"""
    user = get_current_user()
    if user.user_type != 'super_admin':
        return jsonify({'error': '需要超级管理员权限'}), 403
    
    data = request.get_json()
    
    if db.session.query(User).filter(User.username == data['username']).first():
        return jsonify({'error': '用户名已存在'}), 400
    
    new_user = User(
        username=data['username'],
        password_hash=generate_password_hash(data['password']),
        email=data.get('email'),
        user_type=data.get('user_type', 'normal'),
        is_active=True
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user': {
            'id': new_user.id,
            'username': new_user.username,
            'user_type': new_user.user_type
        }
    })

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@require_login
def api_update_user(user_id):
    """更新用户信息"""
    user = get_current_user()
    if user.user_type != 'super_admin':
        return jsonify({'error': '需要超级管理员权限'}), 403
    
    target_user = db.session.query(User).get(user_id)
    if not target_user:
        return jsonify({'error': '用户不存在'}), 404
    
    data = request.get_json()
    
    if 'email' in data:
        target_user.email = data['email']
    if 'user_type' in data:
        target_user.user_type = data['user_type']
    if 'is_active' in data:
        target_user.is_active = data['is_active']
    if 'password' in data:
        target_user.password_hash = generate_password_hash(data['password'])
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_login
def api_delete_user(user_id):
    """删除用户"""
    user = get_current_user()
    if user.user_type != 'super_admin':
        return jsonify({'error': '需要超级管理员权限'}), 403
    
    if user_id == user.id:
        return jsonify({'error': '不能删除当前登录用户'}), 400
    
    target_user = db.session.query(User).get(user_id)
    if not target_user:
        return jsonify({'error': '用户不存在'}), 404
    
    db.session.delete(target_user)
    db.session.commit()
    
    return jsonify({'success': True})

# ==================== 权限管理 API ====================

@app.route('/api/permissions', methods=['GET'])
@require_login
def api_permissions():
    """获取当前用户的权限"""
    user = get_current_user()
    permissions = access_control.permission_manager.get_user_permissions(user.id)
    return jsonify({'permissions': permissions})

@app.route('/api/permissions/<int:data_source_id>', methods=['POST'])
@require_login
def api_grant_permission(data_source_id):
    """授予权限"""
    user = get_current_user()
    if user.user_type != 'super_admin':
        return jsonify({'error': '需要超级管理员权限'}), 403
    
    data = request.get_json()
    
    result = access_control.permission_manager.grant_permission(
        user_id=data['user_id'],
        data_source_id=data_source_id,
        can_view_header=data.get('can_view_header', True),
        can_query=data.get('can_query', True),
        can_import=data.get('can_import', False),
        can_edit_schema=data.get('can_edit_schema', False)
    )
    
    return jsonify(result)

@app.route('/api/permissions/<int:data_source_id>/<int:user_id>', methods=['DELETE'])
@require_login
def api_revoke_permission(data_source_id, user_id):
    """撤销权限"""
    user = get_current_user()
    if user.user_type != 'super_admin':
        return jsonify({'error': '需要超级管理员权限'}), 403
    
    result = access_control.permission_manager.revoke_permission(user_id, data_source_id)
    return jsonify(result)

@app.route('/api/tables/<int:table_id>/statistics', methods=['GET'])
@require_login
def api_table_statistics(table_id):
    """获取表的统计信息"""
    try:
        table_info = query_engine.get_table_info(table_id)
        if not table_info:
            return jsonify({'error': '表不存在'}), 404
        
        # 获取记录数
        from database.schema import TableDataRecord
        record_count = db.session.query(TableDataRecord).filter(
            TableDataRecord.table_id == table_id
        ).count()
        
        return jsonify({
            'table_id': table_id,
            'table_name': table_info['table_name'],
            'display_name': table_info['display_name'],
            'record_count': record_count,
            'column_count': len(table_info['columns']),
            'created_at': table_info['created_at'],
            'updated_at': table_info['updated_at']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data-sources/<int:data_source_id>/statistics', methods=['GET'])
@require_login
def api_data_source_statistics(data_source_id):
    """获取数据源的统计信息"""
    try:
        data_source_info = query_engine.get_data_source_info(data_source_id)
        if not data_source_info:
            return jsonify({'error': '数据源不存在'}), 404
        
        return jsonify(data_source_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/statistics', methods=['GET'])
@require_login
def api_system_statistics():
    """获取系统统计信息"""
    user = get_current_user()
    if user.user_type != 'super_admin':
        return jsonify({'error': '需要超级管理员权限'}), 403
    
    try:
        stats = query_engine.get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/import-history', methods=['GET'])
@require_login
def api_import_history():
    """获取导入历史"""
    user = get_current_user()
    
    try:
        # 获取查询参数
        data_source_id = request.args.get('data_source_id', type=int)
        limit = request.args.get('limit', 20, type=int)
        
        query = db.session.query(ImportLog)
        
        if data_source_id:
            query = query.filter(ImportLog.data_source_id == data_source_id)
        
        # 如果不是超级管理员，只能看到自己导入的记录
        if user.user_type != 'super_admin':
            query = query.filter(ImportLog.imported_by_id == user.id)
        
        logs = query.order_by(ImportLog.imported_at.desc()).limit(limit).all()
        
        return jsonify({
            'import_history': [{
                'id': log.id,
                'data_source_id': log.data_source_id,
                'file_name': log.file_name,
                'sheet_name': log.sheet_name,
                'rows_imported': log.rows_imported,
                'status': log.status,
                'error_message': log.error_message,
                'imported_by_id': log.imported_by_id,
                'imported_at': log.imported_at.isoformat()
            } for log in logs]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='页面不存在'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='服务器内部错误'), 500

if __name__ == '__main__':
    print("=" * 60)
    print("动态材料数据库系统")
    print("=" * 60)
    print("访问地址: http://localhost:5000")
    print("默认管理员: admin / admin123")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
