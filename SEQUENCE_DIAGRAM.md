# Endcrawl 前后端协作流程序列图

## 1. Credits 页面 - Google Sheets 直接编辑流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant CreditsPage as Credits页面
    participant GoogleSheets as Google Sheets<br/>(iframe)
    participant GoogleAPI as Google API<br/>(docs.google.com)

    User->>CreditsPage: 打开 Credits 页面
    CreditsPage->>GoogleSheets: 加载 iframe<br/>(嵌入 Google Sheets)
    GoogleSheets->>GoogleAPI: 请求表格数据
    GoogleAPI-->>GoogleSheets: 返回表格数据
    GoogleSheets-->>CreditsPage: 显示表格界面
    
    User->>GoogleSheets: 在 iframe 中编辑表格
    GoogleSheets->>GoogleAPI: 发送编辑请求<br/>(POST /bind)
    GoogleAPI->>GoogleAPI: 保存到 Google Drive
    GoogleAPI-->>GoogleSheets: 确认保存成功
    GoogleSheets-->>User: 显示更新后的数据
    
    Note over CreditsPage,GoogleAPI: 此流程不经过 Endcrawl 后端
```

## 2. Layout 页面 - 同步 Google Sheets 数据流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant LayoutPage as Layout页面<br/>(前端)
    participant BackendAPI as Endcrawl后端<br/>(/api/project/.../sync/)
    participant GoogleSheetsAPI as Google Sheets API
    participant Database as 数据库

    User->>LayoutPage: 点击"同步"按钮
    LayoutPage->>LayoutPage: 显示进度模态框<br/>("Exporting Google Sheet")
    
    LayoutPage->>BackendAPI: POST /sync/<br/>(csrf_token)
    activate BackendAPI
    
    BackendAPI->>Database: 查询项目配置<br/>(获取 Google Sheet ID)
    Database-->>BackendAPI: 返回 Sheet ID
    
    BackendAPI->>GoogleSheetsAPI: 调用 Google Sheets API<br/>(获取表格数据)
    activate GoogleSheetsAPI
    GoogleSheetsAPI-->>BackendAPI: 返回表格数据
    deactivate GoogleSheetsAPI
    
    BackendAPI->>BackendAPI: 处理/转换数据格式
    BackendAPI->>Database: 保存处理后的数据<br/>(更新 blocks, credits)
    Database-->>BackendAPI: 确认保存成功
    
    BackendAPI-->>LayoutPage: 返回完整项目数据<br/>(rsp.project)
    deactivate BackendAPI
    
    LayoutPage->>LayoutPage: 更新 model.project<br/>(self.model.project = rsp.project)
    LayoutPage->>LayoutPage: 调用 update_preview()<br/>(使用 Nunjucks 重新渲染)
    LayoutPage->>LayoutPage: 更新 DOM<br/>($credits.html(html))
    LayoutPage-->>User: 显示同步后的预览
```

## 3. Layout 页面 - 数据保存流程（SaveQueue）

```mermaid
sequenceDiagram
    participant User as 用户
    participant LayoutPage as Layout页面
    participant SaveQueue as SaveQueue<br/>(保存队列)
    participant BackendAPI as Endcrawl后端<br/>(/api/project/.../)
    participant Database as 数据库

    User->>LayoutPage: 修改区块/卡片/演职员表
    LayoutPage->>LayoutPage: 更新 model.project
    LayoutPage->>SaveQueue: enqueue(record)<br/>(添加到队列)
    
    Note over SaveQueue: 防抖处理<br/>(500ms)
    
    SaveQueue->>SaveQueue: 合并相同记录的更新
    SaveQueue->>BackendAPI: AJAX PUT/POST<br/>(发送数据 + csrf_token)
    activate BackendAPI
    
    BackendAPI->>Database: 保存数据
    Database-->>BackendAPI: 确认保存
    
    BackendAPI-->>SaveQueue: 返回成功响应
    deactivate BackendAPI
    
    SaveQueue->>LayoutPage: 更新保存状态<br/>("Saved")
    SaveQueue->>LayoutPage: 触发 update_preview()<br/>(可选，实时预览)
    LayoutPage-->>User: 显示更新后的预览
```

## 4. Layout 页面 - 页面初始加载流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Browser as 浏览器
    participant BackendServer as Endcrawl后端<br/>(服务器端渲染)
    participant Database as 数据库
    participant LayoutPage as Layout页面<br/>(前端 JS)

    User->>Browser: 访问 /layout/ 页面
    Browser->>BackendServer: GET /app/project/.../layout/
    
    BackendServer->>Database: 查询项目数据<br/>(project, cards, blocks, credits)
    Database-->>BackendServer: 返回完整数据
    
    BackendServer->>BackendServer: 使用 Nunjucks 渲染 HTML<br/>(服务器端)
    BackendServer->>BackendServer: 注入 JavaScript 变量<br/>(var project = {...})
    BackendServer-->>Browser: 返回完整 HTML<br/>(包含数据和脚本)
    
    Browser->>Browser: 解析 HTML
    Browser->>Browser: 执行 JavaScript<br/>(初始化 Layout 应用)
    
    Browser->>LayoutPage: 读取 project 变量<br/>(从服务器注入)
    LayoutPage->>LayoutPage: 初始化 model.project
    LayoutPage->>LayoutPage: 初始化 Nunjucks<br/>(templater)
    LayoutPage->>LayoutPage: 调用 update_preview()<br/>(首次渲染)
    LayoutPage->>LayoutPage: 渲染预览区域<br/>(使用 Nunjucks 模板)
    LayoutPage-->>User: 显示完整页面和预览
```

## 5. 完整数据流转图

```mermaid
sequenceDiagram
    participant User as 用户
    participant CreditsPage as Credits页面
    participant LayoutPage as Layout页面
    participant Backend as Endcrawl后端
    participant GoogleSheets as Google Sheets
    participant Database as 数据库

    Note over User,Database: === 阶段1: 数据输入 ===
    User->>CreditsPage: 在 Google Sheets 中编辑
    CreditsPage->>GoogleSheets: 直接保存（iframe）
    GoogleSheets->>GoogleSheets: 云端存储
    
    Note over User,Database: === 阶段2: 数据同步 ===
    User->>LayoutPage: 点击同步按钮
    LayoutPage->>Backend: POST /sync/
    Backend->>GoogleSheets: Google Sheets API<br/>(获取最新数据)
    GoogleSheets-->>Backend: 返回表格数据
    Backend->>Database: 保存到数据库
    Backend-->>LayoutPage: 返回 project 数据
    LayoutPage->>LayoutPage: 更新 model.project
    LayoutPage->>LayoutPage: Nunjucks 重新渲染
    LayoutPage-->>User: 显示更新后的预览
    
    Note over User,Database: === 阶段3: 数据编辑 ===
    User->>LayoutPage: 修改布局/样式
    LayoutPage->>LayoutPage: 更新 model.project
    LayoutPage->>Backend: SaveQueue 发送更新
    Backend->>Database: 保存修改
    Backend-->>LayoutPage: 确认保存
    LayoutPage->>LayoutPage: 实时更新预览
    
    Note over User,Database: === 阶段4: 最终渲染 ===
    User->>LayoutPage: 点击"渲染"按钮
    LayoutPage->>Backend: POST /render/
    Backend->>Database: 读取最终数据
    Backend->>Backend: 使用渲染引擎生成视频<br/>(可能是 Skia/FFmpeg)
    Backend-->>LayoutPage: 返回渲染结果
    LayoutPage-->>User: 显示下载链接
```

## 关键技术点总结

### 前端渲染技术
- **Credits 页面**: iframe 直接嵌入 Google Sheets（无后端参与）
- **Layout 页面**: Nunjucks 模板引擎 + 客户端渲染
- **数据更新**: 通过 AJAX 与后端 API 交互

### 后端处理技术
- **数据同步**: 调用 Google Sheets API 获取数据
- **数据存储**: 保存到数据库
- **服务器端渲染**: 初始页面使用 Nunjucks 生成 HTML

### 数据一致性保证
- **共享模板**: 前后端使用相同的 Nunjucks 模板
- **统一数据模型**: `project` 对象结构一致
- **实时同步**: 同步后立即更新前端模型

### 渲染流程
1. **预览渲染**: 前端 Nunjucks 实时渲染（快速反馈）
2. **最终渲染**: 后端专用渲染引擎（高质量输出）

