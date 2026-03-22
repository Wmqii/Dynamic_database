"""
用户权限管理模块
实现用户认证、权限分配和访问控制
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import Session

class UserAuthManager:
    """用户认证管理器"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_user(self, username: str, password: str, email: str = None, 
                    user_type: str = 'normal') -> Dict[str, Any]:
        """创建新用户"""
        from database.schema import User
        
        # 检查用户名是否已存在
        existing = self.session.query(User).filter(User.username == username).first()
        if existing:
            return {'success': False, 'error': '用户名已存在'}
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            email=email,
            user_type=user_type,
            is_active=True
        )
        
        self.session.add(user)
        self.session.commit()
        
        return {
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type
            }
        }
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户登录认证"""
        from database.schema import User
        
        user = self.session.query(User).filter(User.username == username).first()
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if check_password_hash(user.password_hash, password):
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type
            }
        
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取用户信息"""
        from database.schema import User
        
        user = self.session.query(User).get(user_id)
        if not user:
            return None
        
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'user_type': user.user_type,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat()
        }
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """获取所有用户列表"""
        from database.schema import User
        
        users = self.session.query(User).all()
        return [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'user_type': user.user_type,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat()
        } for user in users]
    
    def update_user(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """更新用户信息"""
        from database.schema import User
        
        user = self.session.query(User).get(user_id)
        if not user:
            return {'success': False, 'error': '用户不存在'}
        
        allowed_fields = ['email', 'is_active', 'user_type']
        for key, value in kwargs.items():
            if key in allowed_fields and hasattr(user, key):
                setattr(user, key, value)
        
        if 'password' in kwargs:
            user.password_hash = generate_password_hash(kwargs['password'])
        
        self.session.commit()
        return {'success': True, 'user': self.get_user_by_id(user_id)}
    
    def deactivate_user(self, user_id: int) -> Dict[str, Any]:
        """禁用用户"""
        return self.update_user(user_id, is_active=False)
    
    def activate_user(self, user_id: int) -> Dict[str, Any]:
        """启用用户"""
        return self.update_user(user_id, is_active=True)
    
    def delete_user(self, user_id: int) -> Dict[str, Any]:
        """删除用户"""
        from database.schema import User
        
        user = self.session.query(User).get(user_id)
        if not user:
            return {'success': False, 'error': '用户不存在'}
        
        # 不能删除自己
        from flask import session as flask_session
        current_user_id = flask_session.get('user_id')
        if user_id == current_user_id:
            return {'success': False, 'error': '不能删除当前登录用户'}
        
        self.session.delete(user)
        self.session.commit()
        return {'success': True}

class PermissionManager:
    """权限管理器 - 管理用户对数据源的访问权限"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def grant_permission(self, user_id: int, data_source_id: int,
                         can_view_header: bool = True,
                         can_query: bool = True,
                         can_import: bool = False,
                         can_edit_schema: bool = False) -> Dict[str, Any]:
        """授予用户对数据源的访问权限"""
        from database.schema import UserTablePermission
        
        # 检查是否已有权限记录
        existing = self.session.query(UserTablePermission).filter(
            UserTablePermission.user_id == user_id,
            UserTablePermission.data_source_id == data_source_id
        ).first()
        
        if existing:
            # 更新现有权限
            existing.can_view_header = can_view_header
            existing.can_query = can_query
            existing.can_import = can_import
            existing.can_edit_schema = can_edit_schema
            self.session.commit()
            return {'success': True, 'permission_id': existing.id, 'updated': True}
        
        # 创建新权限记录
        permission = UserTablePermission(
            user_id=user_id,
            data_source_id=data_source_id,
            can_view_header=can_view_header,
            can_query=can_query,
            can_import=can_import,
            can_edit_schema=can_edit_schema
        )
        
        self.session.add(permission)
        self.session.commit()
        
        return {'success': True, 'permission_id': permission.id, 'updated': False}
    
    def revoke_permission(self, user_id: int, data_source_id: int) -> Dict[str, Any]:
        """撤销用户对数据源的访问权限"""
        from database.schema import UserTablePermission
        
        permission = self.session.query(UserTablePermission).filter(
            UserTablePermission.user_id == user_id,
            UserTablePermission.data_source_id == data_source_id
        ).first()
        
        if not permission:
            return {'success': False, 'error': '权限记录不存在'}
        
        self.session.delete(permission)
        self.session.commit()
        return {'success': True}
    
    def get_user_permissions(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的所有权限"""
        from database.schema import UserTablePermission, DataSource
        
        permissions = self.session.query(UserTablePermission).filter(
            UserTablePermission.user_id == user_id
        ).all()
        
        result = []
        for perm in permissions:
            data_source = self.session.query(DataSource).get(perm.data_source_id)
            result.append({
                'id': perm.id,
                'data_source_id': perm.data_source_id,
                'data_source_name': data_source.name if data_source else 'Unknown',
                'can_view_header': perm.can_view_header,
                'can_query': perm.can_query,
                'can_import': perm.can_import,
                'can_edit_schema': perm.can_edit_schema
            })
        
        return result
    
    def get_data_source_permissions(self, data_source_id: int) -> List[Dict[str, Any]]:
        """获取数据源的所有权限"""
        from database.schema import UserTablePermission, User
        
        permissions = self.session.query(UserTablePermission).filter(
            UserTablePermission.data_source_id == data_source_id
        ).all()
        
        result = []
        for perm in permissions:
            user = self.session.query(User).get(perm.user_id)
            result.append({
                'id': perm.id,
                'user_id': perm.user_id,
                'username': user.username if user else 'Unknown',
                'can_view_header': perm.can_view_header,
                'can_query': perm.can_query,
                'can_import': perm.can_import,
                'can_edit_schema': perm.can_edit_schema
            })
        
        return result
    
    def check_permission(self, user_id: int, data_source_id: int, 
                         permission_type: str) -> bool:
        """检查用户是否拥有特定权限"""
        from database.schema import User, UserTablePermission
        
        # 超级管理员拥有所有权限
        user = self.session.query(User).get(user_id)
        if user and user.user_type == 'super_admin':
            return True
        
        # 检查具体权限
        permission = self.session.query(UserTablePermission).filter(
            UserTablePermission.user_id == user_id,
            UserTablePermission.data_source_id == data_source_id
        ).first()
        
        if not permission:
            return False
        
        permission_map = {
            'view_header': permission.can_view_header,
            'query': permission.can_query,
            'import': permission.can_import,
            'edit_schema': permission.can_edit_schema
        }
        
        return permission_map.get(permission_type, False)
    
    def get_accessible_data_sources(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户有权限访问的所有数据源"""
        from database.schema import User, UserTablePermission, DataSource
        
        user = self.session.query(User).get(user_id)
        
        # 超级管理员可以访问所有数据源
        if user and user.user_type == 'super_admin':
            data_sources = self.session.query(DataSource).all()
        else:
            # 普通用户只能访问有权限的数据源
            permissions = self.session.query(UserTablePermission).filter(
                UserTablePermission.user_id == user_id
            ).all()
            data_source_ids = [p.data_source_id for p in permissions]
            data_sources = self.session.query(DataSource).filter(
                DataSource.id.in_(data_source_ids)
            ).all()
        
        return [{
            'id': ds.id,
            'name': ds.name,
            'description': ds.description,
            'created_at': ds.created_at.isoformat()
        } for ds in data_sources]

class AccessControlService:
    """访问控制服务 - 整合认证和权限管理"""
    
    def __init__(self, session: Session):
        self.session = session
        self.auth_manager = UserAuthManager(session)
        self.permission_manager = PermissionManager(session)
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        result = self.auth_manager.authenticate(username, password)
        
        if result:
            return {
                'success': True,
                'user': result,
                'message': '登录成功'
            }
        else:
            return {
                'success': False,
                'error': '用户名或密码错误'
            }
    
    def logout(self):
        """用户登出"""
        pass  # Flask session management handled separately
    
    def register_user(self, username: str, password: str, email: str = None) -> Dict[str, Any]:
        """注册新用户"""
        return self.auth_manager.create_user(username, password, email, 'normal')
    
    def require_permission(self, user_id: int, data_source_id: int, 
                           permission_type: str) -> Dict[str, Any]:
        """检查权限（用于API装饰器）"""
        has_permission = self.permission_manager.check_permission(
            user_id, data_source_id, permission_type
        )
        
        if has_permission:
            return {'success': True}
        
        return {
            'success': False,
            'error': f'没有 {permission_type} 权限'
        }
    
    def is_admin(self, user_id: int) -> bool:
        """检查是否为管理员"""
        from database.schema import User
        
        user = self.session.query(User).get(user_id)
        return user and user.user_type in ['super_admin', 'admin']
