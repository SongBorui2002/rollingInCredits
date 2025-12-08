# RollingInCredits

企业级片尾字幕（End Credits）制作工具，支持专业视频格式和精确的色彩管理。

## 📋 项目简介

RollingInCredits 是一个专为电影和电视制作人设计的片尾字幕制作工具，提供直观的 Web 界面用于创建、编辑和管理高质量的片尾字幕。支持多种专业视频格式输出，并集成 OpenColorIO (OCIO) 进行精确的色彩管理。

## ✨ 核心特性

### 字幕编辑
- 🎨 直观的可视化编辑器
- 📝 实时文本编辑和样式调整
- 🎯 精确的像素级定位
- 🔄 拖拽式布局调整
- 📋 批量导入和编辑
- 🔍 搜索和过滤功能

### 专业格式支持
- **DPX** - 数字图像交换格式
- **EXR** - OpenEXR 高动态范围格式
- **TIFF** - 高质量图像格式
- **ProRes 4444** - Apple ProRes 专业视频格式

### 色彩管理
- 🎨 **OpenColorIO (OCIO)** 集成
- 🌈 支持多种色彩空间（Rec.709, P3-D65, Rec.2020, ACES 等）
- 🎯 精确的白点转换
- 📊 传递函数管理（Gamma, PQ, HLG）
- 🔄 色彩空间转换

### 协作功能
- 👥 多用户实时协作编辑
- 💬 评论和审核流程
- 📝 版本历史管理
- 🔐 权限控制

### 预览与渲染
- 👁️ 实时预览功能
- 🎬 高质量预览帧渲染
- ⚡ 快速预览（低分辨率）
- 🎞️ 最终渲染（全分辨率）

## 🏗️ 技术架构

### 前端
- **框架**: React / Next.js
- **UI 库**: Tailwind CSS
- **渲染**: Canvas API（交互层）
- **实时通信**: WebSocket
- **状态管理**: Zustand / Redux

### 后端
- **框架**: FastAPI (Python) / Express (Node.js)
- **渲染引擎**: OpenImageIO (OIIO)
- **色彩管理**: OpenColorIO (OCIO)
- **视频编码**: FFmpeg
- **任务队列**: Celery (Python) / Bull (Node.js)
- **数据库**: PostgreSQL + Redis

### 通信协议
- **WebSocket**: 实时编辑同步、协作
- **REST API**: 项目保存、加载、渲染请求
- **Server-Sent Events (SSE)**: 渲染进度推送

## 📡 前后端通信技术选型

本项目采用**混合通信策略**，根据不同场景选择最适合的通信技术。

### 可用的通信技术

#### 1. REST API (HTTP/HTTPS)
**特点**:
- ✅ 无状态、简单易用
- ✅ 广泛支持，易于调试
- ✅ 支持缓存
- ❌ 单向通信（请求-响应）
- ❌ 需要轮询才能实现"实时"效果
- ❌ 每次请求都有 HTTP 头开销

**适用场景**:
- 项目保存/加载
- 用户认证
- 获取项目列表
- 提交渲染任务
- 下载文件

**示例**:
```typescript
// 保存项目
POST /api/projects/{id}/save
{
  "subtitles": [...],
  "settings": {...}
}

// 获取项目
GET /api/projects/{id}
```

#### 2. WebSocket
**特点**:
- ✅ 全双工通信（双向）
- ✅ 低延迟，实时性好
- ✅ 持久连接，减少握手开销
- ✅ 服务器可以主动推送
- ❌ 需要维护连接状态
- ❌ 某些代理/防火墙可能不支持
- ❌ 连接断开需要重连机制

**适用场景**:
- 实时编辑同步（多用户协作）
- 实时预览更新
- 实时通知
- 聊天/评论功能

**示例**:
```typescript
// 建立连接
const ws = new WebSocket('wss://api.example.com/ws');

// 发送编辑操作
ws.send(JSON.stringify({
  type: 'subtitle_update',
  data: { id: '1', x: 100, y: 200 }
}));

// 接收实时更新
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  // 更新 UI
};
```

#### 3. Server-Sent Events (SSE)
**特点**:
- ✅ 服务器到客户端的单向推送
- ✅ 自动重连机制
- ✅ 基于 HTTP，兼容性好
- ✅ 比 WebSocket 更简单
- ❌ 只能服务器推送到客户端
- ❌ 不支持客户端到服务器的实时通信

**适用场景**:
- 渲染进度推送
- 任务状态更新
- 通知推送
- 日志流

**示例**:
```typescript
// 监听渲染进度
const eventSource = new EventSource('/api/render-jobs/123/progress');

eventSource.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  updateProgressBar(progress.percentage);
};
```

#### 4. GraphQL (可选)
**特点**:
- ✅ 灵活的查询
- ✅ 减少网络请求
- ✅ 类型安全
- ❌ 学习曲线
- ❌ 缓存复杂

**适用场景**:
- 复杂数据查询
- 移动端 API（如果未来支持）

#### 5. gRPC (可选)
**特点**:
- ✅ 高性能
- ✅ 类型安全
- ✅ 流式传输
- ❌ 浏览器支持有限（需要 gRPC-Web）
- ❌ 调试相对困难

**适用场景**:
- 微服务间通信
- 高性能场景

### 为什么选择 WebSocket？

#### 核心需求分析

1. **实时协作编辑**
   - 多用户同时编辑同一项目
   - 需要实时同步编辑操作
   - **WebSocket 优势**: 双向通信，低延迟

2. **实时预览更新**
   - 用户编辑时，需要快速看到预览
   - 后端渲染预览帧后需要推送给前端
   - **WebSocket 优势**: 服务器主动推送

3. **实时通知**
   - 其他用户的编辑操作
   - 系统通知
   - **WebSocket 优势**: 实时推送

#### 技术对比

| 特性 | REST API | WebSocket | SSE |
|------|----------|-----------|-----|
| 实时性 | ❌ 需要轮询 | ✅ 实时 | ✅ 实时（单向） |
| 双向通信 | ❌ | ✅ | ❌ |
| 连接开销 | 每次请求 | 一次连接 | 一次连接 |
| 服务器推送 | ❌ | ✅ | ✅ |
| 浏览器支持 | ✅ 完美 | ✅ 良好 | ✅ 良好 |
| 调试难度 | ⭐ 简单 | ⭐⭐ 中等 | ⭐ 简单 |
| 适用场景 | CRUD 操作 | 实时协作 | 进度推送 |

### 混合通信策略

本项目采用**混合策略**，根据场景选择最合适的技术：

```
┌─────────────────────────────────────────────────┐
│              前端应用                            │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  REST API                                │  │
│  │  - 项目 CRUD                             │  │
│  │  - 用户认证                              │  │
│  │  - 文件上传/下载                         │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  WebSocket                               │  │
│  │  - 实时编辑同步                           │  │
│  │  - 协作通知                               │  │
│  │  - 实时预览更新                           │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Server-Sent Events                     │  │
│  │  - 渲染进度                               │  │
│  │  - 任务状态                               │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 具体使用场景

#### 场景 1: 用户编辑字幕
```typescript
// 使用 WebSocket - 需要实时同步
ws.send({
  type: 'subtitle_update',
  data: { id: '1', text: 'New Text', x: 100, y: 200 }
});
```

#### 场景 2: 保存项目
```typescript
// 使用 REST API - 不需要实时性
await fetch('/api/projects/123/save', {
  method: 'POST',
  body: JSON.stringify(projectData)
});
```

#### 场景 3: 提交渲染任务
```typescript
// 使用 REST API - 创建任务
const response = await fetch('/api/render', {
  method: 'POST',
  body: JSON.stringify(renderConfig)
});
const { jobId } = await response.json();

// 使用 SSE - 监听进度
const eventSource = new EventSource(`/api/render-jobs/${jobId}/progress`);
```

#### 场景 4: 多用户协作
```typescript
// 使用 WebSocket - 实时同步
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'user_edit') {
    // 实时更新其他用户的编辑
    updateSubtitleFromOtherUser(message.data);
  }
};
```

### 为什么不只用 WebSocket？

虽然 WebSocket 功能强大，但**不适合所有场景**：

1. **简单 CRUD 操作**: REST API 更简单、更符合 RESTful 原则
2. **缓存需求**: REST API 可以利用 HTTP 缓存
3. **调试便利**: REST API 更容易调试（浏览器开发者工具）
4. **无状态操作**: 某些操作不需要保持连接状态
5. **资源消耗**: WebSocket 需要维护连接，简单操作用 REST 更轻量

### 实现建议

#### WebSocket 连接管理
```typescript
class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect() {
    this.ws = new WebSocket('wss://api.example.com/ws');
    
    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      console.log('WebSocket connected');
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      // 自动重连
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect();
        }, 1000 * this.reconnectAttempts);
      }
    };
  }
  
  send(message: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // 队列消息或使用 REST API 降级
      this.queueMessage(message);
    }
  }
}
```

#### 降级策略
```typescript
// 如果 WebSocket 不可用，降级到 REST API 轮询
if (!websocketAvailable) {
  // 使用 REST API + 轮询
  setInterval(() => {
    fetch('/api/projects/123/updates')
      .then(r => r.json())
      .then(updates => applyUpdates(updates));
  }, 1000);
}
```

### 总结

- **WebSocket**: 用于需要实时双向通信的场景（协作编辑、实时预览）
- **REST API**: 用于传统的 CRUD 操作（保存、加载、认证）
- **SSE**: 用于服务器到客户端的单向推送（进度、通知）

这种混合策略既保证了实时性，又保持了系统的简洁性和可维护性。

## 📐 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                      前端 (Web)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  编辑器 UI   │  │  Canvas 预览  │  │  交互层      │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │         │
│         └──────────────────┴──────────────────┘         │
│                         │                               │
│                    WebSocket / REST API                  │
└─────────────────────────┼───────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────┐
│                      后端服务                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  API 服务器  │  │  渲染引擎     │  │  任务队列    │ │
│  │  (FastAPI)   │  │  (OIIO+OCIO)  │  │  (Celery)    │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │         │
│         └──────────────────┴──────────────────┘         │
│                         │                               │
│                    ┌────┴────┐                          │
│                    │  FFmpeg │                          │
│                    │ (编码)  │                          │
│                    └─────────┘                          │
└─────────────────────────────────────────────────────────┘
```

## 🔄 渲染流程

### 预览渲染流程
```
1. 用户编辑字幕 → 前端 Canvas 交互层更新
2. WebSocket 发送配置到后端
3. 后端使用 OIIO + OCIO 渲染预览帧（低分辨率）
4. 返回预览帧 URL
5. 前端显示预览帧
```

### 最终渲染流程
```
1. 用户确认并请求渲染
2. 后端创建渲染任务（队列）
3. OIIO + OCIO 渲染全分辨率图像序列
   - 文本渲染（Cairo/PIL）
   - 色彩空间转换（OCIO）
   - 图像合成
4. FFmpeg 编码为 ProRes4444（或其他格式）
5. 返回下载链接
```

## 🎯 渲染一致性保证

为确保预览与最终渲染的一致性，采用以下策略：

### 核心原则
- **统一渲染引擎**: 预览和最终输出都使用后端 OIIO + OCIO 渲染
- **相同字体文件**: 前后端使用相同的字体文件
- **精确配置**: 使用像素级精确配置，避免相对单位
- **色彩空间管理**: 预览使用 sRGB，最终输出使用目标色彩空间（通过 OCIO）

### 技术实现
- 前端 Canvas 仅用于交互层（拖拽、选择框）
- 预览帧由后端渲染，确保与最终输出一致
- 使用相同的字体引擎和渲染算法

## 📦 安装与运行

### 前置要求
- Python 3.9+
- Node.js 18+
- FFmpeg (支持 ProRes)
- OpenImageIO
- OpenColorIO
- PostgreSQL
- Redis

### 安装步骤

#### 1. 克隆项目
```bash
git clone <repository-url>
cd rollingInCredits
```

#### 2. 后端设置
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. 前端设置
```bash
cd frontend
npm install
```

#### 4. 环境配置
```bash
# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件，配置数据库、Redis 等
```

#### 5. 数据库初始化
```bash
cd backend
alembic upgrade head
```

#### 6. 运行服务
```bash
# 后端
cd backend
uvicorn app.main:app --reload

# 前端
cd frontend
npm run dev

# 任务队列（Celery）
cd backend
celery -A app.tasks worker --loglevel=info
```

## 🚀 使用指南

### 创建新项目
1. 登录系统
2. 点击"新建项目"
3. 设置项目名称、分辨率、帧率等参数
4. 选择色彩空间配置（OCIO 配置文件）

### 编辑字幕
1. 添加字幕条目
2. 编辑文本内容
3. 调整位置（拖拽或输入坐标）
4. 设置样式（字体、大小、颜色等）
5. 实时预览效果

### 渲染输出
1. 确认字幕内容
2. 选择输出格式（DPX/EXR/TIFF/ProRes4444）
3. 选择色彩空间
4. 提交渲染任务
5. 等待渲染完成并下载

## 🔧 开发指南

### 项目结构
```
rollingInCredits/
├── frontend/          # 前端代码
│   ├── src/
│   │   ├── components/    # React 组件
│   │   ├── hooks/        # 自定义 Hooks
│   │   ├── stores/       # 状态管理
│   │   ├── utils/         # 工具函数
│   │   └── api/          # API 调用
│   └── public/
├── backend/           # 后端代码
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── core/         # 核心配置
│   │   ├── models/        # 数据模型
│   │   ├── services/     # 业务逻辑
│   │   ├── render/       # 渲染引擎
│   │   └── tasks/        # 异步任务
│   └── alembic/          # 数据库迁移
├── shared/            # 共享代码
│   └── types/            # TypeScript 类型定义
└── docs/              # 文档
```

### 代码规范
- 前端: ESLint + Prettier
- 后端: Black + isort + mypy
- 提交信息: Conventional Commits

### 测试
```bash
# 前端测试
cd frontend
npm test

# 后端测试
cd backend
pytest
```

## 📝 API 文档

API 文档在运行后端服务后可通过以下地址访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🔒 安全考虑

- ProRes 格式使用需注意 Apple 许可要求
- 用户数据加密存储
- API 认证和授权
- 文件上传大小限制
- 渲染任务队列限流

## 🐛 已知问题与限制

- 浏览器字体渲染差异：前端预览可能与最终输出有细微差异（通过后端渲染预览帧解决）
- ProRes 编码性能：高分辨率渲染可能需要较长时间
- 字体文件大小：某些字体文件较大，影响加载速度

## 🗺️ 路线图

### Phase 1: MVP
- [x] 基础字幕编辑器
- [x] 简单模板系统
- [x] Canvas 预览
- [x] FFmpeg 视频导出
- [ ] OCIO 色彩管理集成
- [ ] 用户系统

### Phase 2: 增强功能
- [ ] 更多模板和样式
- [ ] 协作功能
- [ ] 版本控制
- [ ] 批量处理

### Phase 3: 高级功能
- [ ] 高级动画效果
- [ ] API 开放
- [ ] 插件系统
- [ ] 移动端支持

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

[待定]

## 👥 团队

[待定]

## 📞 联系方式

[待定]

## 🙏 致谢

- OpenImageIO 项目
- OpenColorIO 项目
- FFmpeg 项目
- 所有贡献者和用户

---

**注意**: 本项目仍在积极开发中，API 和功能可能会有变化。

# rollingInCredits
