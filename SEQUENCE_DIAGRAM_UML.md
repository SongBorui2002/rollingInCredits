# Endcrawl 前后端协作流程 - UML 序列图

## 1. Credits 页面 - Google Sheets 直接编辑流程（UML PlantUML 格式）

```plantuml
@startuml CreditsPage_GoogleSheets_Flow
actor User as 用户
participant "Credits页面" as CreditsPage
participant "Google Sheets\n(iframe)" as GoogleSheets
participant "Google API\n(docs.google.com)" as GoogleAPI

用户 -> Credits页面: 打开 Credits 页面
Credits页面 -> GoogleSheets: 加载 iframe\n(嵌入 Google Sheets)
GoogleSheets -> GoogleAPI: 请求表格数据
GoogleAPI --> GoogleSheets: 返回表格数据
GoogleSheets --> Credits页面: 显示表格界面

用户 -> GoogleSheets: 在 iframe 中编辑表格
GoogleSheets -> GoogleAPI: 发送编辑请求\n(POST /bind)
activate GoogleAPI
GoogleAPI -> GoogleAPI: 保存到 Google Drive
GoogleAPI --> GoogleSheets: 确认保存成功
deactivate GoogleAPI
GoogleSheets --> 用户: 显示更新后的数据

note right of Credits页面, GoogleAPI
  此流程不经过 Endcrawl 后端
end note
@enduml
```

## 2. Layout 页面 - 同步 Google Sheets 数据流程（UML PlantUML 格式）

```plantuml
@startuml LayoutPage_Sync_Flow
actor User as 用户
participant "Layout页面\n(前端)" as LayoutPage
participant "Endcrawl后端\n(/api/project/.../sync/)" as BackendAPI
participant "Google Sheets API" as GoogleSheetsAPI
database "数据库" as Database

用户 -> LayoutPage: 点击"同步"按钮
activate LayoutPage
LayoutPage -> LayoutPage: 显示进度模态框\n("Exporting Google Sheet")

LayoutPage -> BackendAPI: POST /sync/\n(csrf_token)
activate BackendAPI

BackendAPI -> Database: 查询项目配置\n(获取 Google Sheet ID)
Database --> BackendAPI: 返回 Sheet ID

BackendAPI -> GoogleSheetsAPI: 调用 Google Sheets API\n(获取表格数据)
activate GoogleSheetsAPI
GoogleSheetsAPI --> BackendAPI: 返回表格数据
deactivate GoogleSheetsAPI

BackendAPI -> BackendAPI: 处理/转换数据格式
BackendAPI -> Database: 保存处理后的数据\n(更新 blocks, credits)
Database --> BackendAPI: 确认保存成功

BackendAPI --> LayoutPage: 返回完整项目数据\n(rsp.project)
deactivate BackendAPI

LayoutPage -> LayoutPage: 更新 model.project\n(self.model.project = rsp.project)
LayoutPage -> LayoutPage: 调用 update_preview()\n(使用 Nunjucks 重新渲染)
LayoutPage -> LayoutPage: 更新 DOM\n($credits.html(html))
LayoutPage --> 用户: 显示同步后的预览
deactivate LayoutPage
@enduml
```

## 3. Layout 页面 - 数据保存流程（SaveQueue）（UML PlantUML 格式）

```plantuml
@startuml LayoutPage_SaveQueue_Flow
actor User as 用户
participant "Layout页面" as LayoutPage
participant "SaveQueue\n(保存队列)" as SaveQueue
participant "Endcrawl后端\n(/api/project/.../)" as BackendAPI
database "数据库" as Database

用户 -> LayoutPage: 修改区块/卡片/演职员表
activate LayoutPage
LayoutPage -> LayoutPage: 更新 model.project
LayoutPage -> SaveQueue: enqueue(record)\n(添加到队列)
activate SaveQueue

note over SaveQueue
  防抖处理\n(500ms)
end note

SaveQueue -> SaveQueue: 合并相同记录的更新
SaveQueue -> BackendAPI: AJAX PUT/POST\n(发送数据 + csrf_token)
activate BackendAPI

BackendAPI -> Database: 保存数据
Database --> BackendAPI: 确认保存

BackendAPI --> SaveQueue: 返回成功响应
deactivate BackendAPI

SaveQueue -> LayoutPage: 更新保存状态\n("Saved")
SaveQueue -> LayoutPage: 触发 update_preview()\n(可选，实时预览)
deactivate SaveQueue
LayoutPage -> LayoutPage: 更新预览
LayoutPage --> 用户: 显示更新后的预览
deactivate LayoutPage
@enduml
```

## 4. Layout 页面 - 页面初始加载流程（UML PlantUML 格式）

```plantuml
@startuml LayoutPage_InitialLoad_Flow
actor User as 用户
participant "浏览器" as Browser
participant "Endcrawl后端\n(服务器端渲染)" as BackendServer
database "数据库" as Database
participant "Layout页面\n(前端 JS)" as LayoutPage

用户 -> Browser: 访问 /layout/ 页面
Browser -> BackendServer: GET /app/project/.../layout/
activate BackendServer

BackendServer -> Database: 查询项目数据\n(project, cards, blocks, credits)
Database --> BackendServer: 返回完整数据

BackendServer -> BackendServer: 使用 Nunjucks 渲染 HTML\n(服务器端)
BackendServer -> BackendServer: 注入 JavaScript 变量\n(var project = {...})
BackendServer --> Browser: 返回完整 HTML\n(包含数据和脚本)
deactivate BackendServer

Browser -> Browser: 解析 HTML
Browser -> Browser: 执行 JavaScript\n(初始化 Layout 应用)
activate Browser

Browser -> LayoutPage: 读取 project 变量\n(从服务器注入)
activate LayoutPage
LayoutPage -> LayoutPage: 初始化 model.project
LayoutPage -> LayoutPage: 初始化 Nunjucks\n(templater)
LayoutPage -> LayoutPage: 调用 update_preview()\n(首次渲染)
LayoutPage -> LayoutPage: 渲染预览区域\n(使用 Nunjucks 模板)
LayoutPage --> 用户: 显示完整页面和预览
deactivate LayoutPage
deactivate Browser
@enduml
```

## 5. 完整数据流转图（UML PlantUML 格式）

```plantuml
@startuml Complete_DataFlow
actor User as 用户
participant "Credits页面" as CreditsPage
participant "Layout页面" as LayoutPage
participant "Endcrawl后端" as Backend
participant "Google Sheets" as GoogleSheets
database "数据库" as Database

== 阶段1: 数据输入 ==
用户 -> CreditsPage: 在 Google Sheets 中编辑
CreditsPage -> GoogleSheets: 直接保存（iframe）
activate GoogleSheets
GoogleSheets -> GoogleSheets: 云端存储
deactivate GoogleSheets

== 阶段2: 数据同步 ==
用户 -> LayoutPage: 点击同步按钮
activate LayoutPage
LayoutPage -> Backend: POST /sync/
activate Backend
Backend -> GoogleSheets: Google Sheets API\n(获取最新数据)
activate GoogleSheets
GoogleSheets --> Backend: 返回表格数据
deactivate GoogleSheets
Backend -> Database: 保存到数据库
Database --> Backend: 确认保存
Backend --> LayoutPage: 返回 project 数据
deactivate Backend
LayoutPage -> LayoutPage: 更新 model.project
LayoutPage -> LayoutPage: Nunjucks 重新渲染
LayoutPage --> 用户: 显示更新后的预览
deactivate LayoutPage

== 阶段3: 数据编辑 ==
用户 -> LayoutPage: 修改布局/样式
activate LayoutPage
LayoutPage -> LayoutPage: 更新 model.project
LayoutPage -> Backend: SaveQueue 发送更新
activate Backend
Backend -> Database: 保存修改
Database --> Backend: 确认保存
Backend --> LayoutPage: 确认保存
deactivate Backend
LayoutPage -> LayoutPage: 实时更新预览
LayoutPage --> 用户: 显示更新后的预览
deactivate LayoutPage

== 阶段4: 最终渲染 ==
用户 -> LayoutPage: 点击"渲染"按钮
activate LayoutPage
LayoutPage -> Backend: POST /render/
activate Backend
Backend -> Database: 读取最终数据
Database --> Backend: 返回数据
Backend -> Backend: 使用渲染引擎生成视频\n(可能是 Skia/FFmpeg)
Backend --> LayoutPage: 返回渲染结果
deactivate Backend
LayoutPage --> 用户: 显示下载链接
deactivate LayoutPage
@enduml
```

## 格式说明

### Mermaid vs UML PlantUML

| 特性 | Mermaid | UML PlantUML |
|------|---------|--------------|
| **语法** | 简化语法 | 标准 UML 语法 |
| **支持** | GitHub/GitLab 原生支持 | 需要 PlantUML 工具 |
| **激活框** | `activate/deactivate` | `activate/deactivate` |
| **注释** | `Note over` | `note right/left` |
| **分组** | `==` | `==` |
| **参与者** | `participant` | `participant` 或 `actor` |

### 如何查看 UML 图

1. **在线工具**：
   - http://www.plantuml.com/plantuml/uml/
   - 复制代码到在线编辑器即可查看

2. **VS Code 插件**：
   - 安装 "PlantUML" 插件
   - 右键选择 "Preview PlantUML"

3. **本地工具**：
   - 安装 PlantUML：`brew install plantuml` (macOS)
   - 或使用 Docker：`docker run -d -p 8080:8080 plantuml/plantuml-server:jetty`

### 两种格式的选择

- **Mermaid**：适合文档、GitHub README、快速查看
- **UML PlantUML**：适合正式文档、需要标准 UML 格式、与 UML 工具集成

两个版本都已提供，可根据需要选择使用。

