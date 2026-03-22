# 动态材料数据库系统

一个基于Flask和SQLAlchemy的现代化材料数据管理平台，支持灵活的动态表结构、Excel数据导入、权限管理和数据查询。

## 🌟 主要特性

### 核心功能
- ✅ **动态表结构**: 无需修改数据库schema即可创建新表
- ✅ **Excel导入**: 支持.xlsx和.xls格式的批量数据导入
- ✅ **灵活查询**: 支持过滤、排序、分页等多种查询方式
- ✅ **数据导出**: 支持CSV和Excel格式导出
- ✅ **权限管理**: 细粒度的用户权限控制
- ✅ **审计日志**: 完整的操作历史记录

### 技术特点
- 🔧 **RESTful API**: 完整的API接口支持程序化访问
- 🔐 **安全认证**: 基于会话的用户认证
- 📊 **数据统计**: 系统级和表级的统计信息
- 🎨 **现代UI**: 响应式设计，支持移动设备
- 📱 **跨平台**: 支持Windows、Linux、macOS

## 📋 系统要求

- Python 3.8 或更高版本
- 4GB 内存（推荐8GB）
- 500MB 磁盘空间
- 现代浏览器（Chrome、Firefox、Safari、Edge）

## 🚀 快速开始

### 1. 克隆或下载项目
```bash
cd material_database
```

### 2. 创建虚拟环境
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 启动应用
```bash
python app.py
```

### 5. 访问系统
打开浏览器访问 `http://localhost:5000`

### 6. 登录
- **用户名**: admin
- **密码**: admin123

## 📚 文档

- [快速开始指南](QUICK_START.md) - 新用户必读
- [API文档](API_DOCUMENTATION.md) - 完整的API参考
- [使用说明](docs/使用说明.md) - 详细的功能说明
- [上传修复总结](UPLOAD_FIX_SUMMARY.md) - 最近的改进

## 🏗️ 项目结构

```
material_database/
├── app.py                          # 主应用程序
├── requirements.txt                # 依赖列表
├── material_database.db            # SQLite数据库
├── database/
│   ├── init_db.py                 # 数据库初始化
│   └── schema.py                  # 数据库模型定义
├── modules/
│   ├── excel_importer.py          # Excel导入模块
│   ├── query_engine.py            # 查询引擎
│   └── user_auth.py               # 用户认证和权限管理
├── templates/                      # HTML模板
│   ├── base.html                  # 基础模板
│   ├── index.html                 # 首页
│   ├── login.html                 # 登录页
│   ├── data_sources.html          # 数据源管理
│   ├── table_view.html            # 表格查看
│   ├── users.html                 # 用户管理
│   ├── permissions.html           # 权限管理
│   ├── admin.html                 # 管理员面板
│   └── register.html              # 注册页
├── uploads/                        # 上传文件目录
├── docs/
│   └── 使用说明.md                # 详细使用文档
└── logs/                          # 应用日志

```

## 🔑 默认账户

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 超级管理员 |
| manager | manager123 | 管理员 |
| viewer | viewer123 | 普通用户 |

## 🎯 主要功能

### 数据源管理
- 创建和管理数据源
- 查看数据源统计信息
- 管理数据源权限

### 数据导入
- 支持Excel文件导入
- 自动数据类型检测
- 导入进度跟踪
- 导入历史记录

### 数据查询
- 灵活的过滤条件
- 多列排序
- 分页显示
- 全文搜索

### 数据导出
- CSV格式导出
- Excel格式导出
- 自定义导出范围

### 权限管理
- 用户角色管理
- 细粒度权限控制
- 权限审计日志
- 权限继承机制

### 系统管理
- 用户管理
- 系统统计
- 操作日志
- 数据备份

## 🔌 API接口

### 认证
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/register` - 用户注册

### 数据源
- `GET /api/data-sources` - 获取数据源列表
- `POST /api/data-sources` - 创建数据源
- `GET /api/data-sources/{id}/statistics` - 获取数据源统计

### 数据表
- `GET /api/tables/{id}` - 获取表信息
- `GET /api/tables/{id}/data` - 查询表数据
- `GET /api/tables/{id}/statistics` - 获取表统计

### 导入
- `POST /api/import` - 导入Excel文件
- `GET /api/import-history` - 获取导入历史

### 权限
- `GET /api/permissions/{data_source_id}` - 获取权限列表
- `POST /api/permissions/{data_source_id}` - 授予权限
- `DELETE /api/permissions/{data_source_id}/{user_id}` - 撤销权限

详见 [API文档](API_DOCUMENTATION.md)

## 🛠️ 配置

### 修改上传文件大小限制
编辑 `app.py`:
```python
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
```

### 修改数据库路径
编辑 `app.py`:
```python
DATABASE_PATH = '/path/to/your/database.db'
```

### 修改监听端口
```bash
python app.py --port 8080
```

## 📊 数据库架构

### 核心表
- **users**: 用户信息
- **data_sources**: 数据源定义
- **dynamic_tables**: 动态表定义
- **table_columns**: 表字段定义
- **table_data_records**: 表数据记录（JSON存储）
- **user_table_permissions**: 用户权限
- **import_logs**: 导入日志

## 🔒 安全特性

- ✅ 密码加密存储
- ✅ 会话管理
- ✅ 权限验证
- ✅ SQL注入防护
- ✅ CSRF保护
- ✅ 操作审计

## 🚀 性能优化

- 分页查询
- 数据库索引
- 缓存机制
- 异步导入（可选）
- 连接池管理

## 🐛 已知问题

- 大文件导入可能较慢（>50MB）
- 不支持实时协作编辑
- 移动端功能有限

## 📝 更新日志

### v1.3.0 (2024-03-20)
- ✨ 改进Excel导入错误处理
- ✨ 添加数据导出功能
- ✨ 改进权限管理
- 🐛 修复上传失败问题
- 📚 完善API文档

### v1.2.0 (2024-02-15)
- ✨ 添加高级查询功能
- ✨ 添加数据统计
- 🐛 修复权限检查问题

### v1.1.0 (2024-01-20)
- ✨ 添加权限管理模块
- ✨ 添加API接口
- 🐛 修复数据导入问题

### v1.0.0 (2024-01-15)
- 🎉 初始版本发布

## 🤝 贡献

欢迎提交问题和改进建议！

## 📄 许可证

MIT License

## 📞 支持

- 📧 Email: support@material.local
- 💬 Issues: GitHub Issues
- 📖 Wiki: 项目Wiki

## 🙏 致谢

感谢所有贡献者和用户的支持！

---

**最后更新**: 2024年3月20日  
**版本**: 1.3.0  
**维护者**: Material Database Team
