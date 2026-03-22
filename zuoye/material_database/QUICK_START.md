# 快速开始指南

## 1. 环境准备

### 系统要求
- Python 3.8 或更高版本
- Windows、Linux 或 macOS
- 至少 4GB 内存
- 至少 500MB 磁盘空间

### 安装依赖
```bash
# 进入项目目录
cd material_database

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install flask flask-sqlalchemy pandas openpyxl werkzeug
```

## 2. 启动应用

```bash
# 确保虚拟环境已激活
python app.py
```

应用将在 `http://localhost:5000` 启动

## 3. 首次登录

- **用户名**: admin
- **密码**: admin123

## 4. 基本操作流程

### 步骤1: 创建数据源
1. 登录系统
2. 点击"数据源管理"
3. 点击"新建数据源"按钮
4. 填写数据源名称和描述
5. 点击"创建"

### 步骤2: 上传Excel文件
1. 在数据源卡片上点击"导入数据"
2. 选择Excel文件（.xlsx 或 .xls）
3. 点击"开始导入"
4. 等待导入完成

### 步骤3: 查看导入的数据
1. 点击数据源卡片查看数据表
2. 点击数据表名称查看详细数据
3. 使用过滤和排序功能查询数据

### 步骤4: 导出数据
1. 在数据表页面点击"导出数据"
2. 选择导出格式（CSV 或 Excel）
3. 文件将自动下载

## 5. Excel文件格式要求

### 支持的格式
- .xlsx (Excel 2007及以后版本)
- .xls (Excel 97-2003)

### 文件要求
- 首行必须包含列标题
- 数据从第二行开始
- 单个文件大小不超过50MB
- 支持多个Sheet

### 示例
```
| 材料名称 | 密度 | 熔点 | 创建日期 |
|---------|------|------|---------|
| 铝合金   | 2.7  | 933  | 2024-01-15 |
| 钢铁     | 7.85 | 1538 | 2024-01-16 |
| 铜合金   | 8.9  | 1358 | 2024-01-17 |
```

## 6. 常见问题

### Q: 上传失败，显示"只支持Excel文件"
**A**: 确保文件扩展名是 .xlsx 或 .xls，不是其他格式

### Q: 导入后看不到数据
**A**: 
1. 确保Excel文件包含有效的Sheet
2. 确保Sheet中有数据（至少2行：标题+数据）
3. 刷新页面重试

### Q: 忘记密码怎么办
**A**: 当前版本没有密码重置功能，请联系管理员

### Q: 如何修改用户密码
**A**: 登录后进入用户设置页面修改密码

### Q: 如何删除数据源
**A**: 在数据源卡片上右键点击或使用管理员功能删除

## 7. 权限管理

### 用户角色
- **超级管理员**: 拥有所有权限
- **管理员**: 可以管理用户和权限
- **普通用户**: 可以查看和导入数据

### 权限类型
- **查看表头**: 查看数据表结构
- **查询数据**: 查看数据表内容
- **导入数据**: 导入Excel文件
- **编辑模式**: 修改表结构

## 8. 数据导出

### 支持的格式
- **CSV**: 逗号分隔值，可用Excel打开
- **Excel**: .xlsx格式，保留格式和公式

### 导出步骤
1. 在数据表页面点击"导出数据"
2. 选择导出格式
3. 文件自动下载

## 9. API使用

### 获取数据源列表
```bash
curl http://localhost:5000/api/data-sources
```

### 查询表数据
```bash
curl "http://localhost:5000/api/tables/1/data?page=1&page_size=20"
```

### 导入Excel文件
```bash
curl -X POST -F "file=@data.xlsx" -F "data_source_id=1" \
  http://localhost:5000/api/import
```

详见 [API文档](API_DOCUMENTATION.md)

## 10. 性能优化建议

### 大文件处理
- 对于超过10MB的文件，建议分割后分批上传
- 避免在高峰期导入大量数据

### 查询优化
- 使用过滤条件缩小查询范围
- 避免一次加载超过1000条记录

### 系统维护
- 定期备份数据库
- 清理过期的导入日志
- 监控磁盘空间使用

## 11. 故障排除

### 应用无法启动
```bash
# 检查Python版本
python --version

# 检查依赖是否安装
pip list

# 查看错误日志
python app.py 2>&1 | tee app.log
```

### 数据库错误
```bash
# 重新初始化数据库
python database/init_db.py --force
```

### 上传文件损坏
```bash
# 清理上传目录
rm -rf uploads/*
```

## 12. 下一步

- 阅读 [完整文档](material_database/docs/使用说明.md)
- 查看 [API文档](API_DOCUMENTATION.md)
- 了解 [系统架构](README.md)

## 13. 获取帮助

- 查看系统日志: `logs/app.log`
- 检查浏览器控制台错误
- 查看服务器输出信息

## 14. 安全建议

1. **修改默认密码**: 首次登录后立即修改admin密码
2. **启用HTTPS**: 在生产环境中使用HTTPS
3. **定期备份**: 定期备份数据库文件
4. **限制访问**: 使用防火墙限制访问
5. **更新依赖**: 定期更新Python依赖包

## 15. 生产部署

### 使用Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 使用Nginx反向代理
```nginx
server {
    listen 80;
    server_name example.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 使用Docker
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

---

**需要帮助?** 查看完整文档或联系系统管理员
