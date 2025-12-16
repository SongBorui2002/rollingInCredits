# Endcrawl 逆向分析（技术栈与原理）

> 基于仓库 `endcrawl`/`endcrawl.credits` 代码与页面抓包的静态逆向分析，梳理其主要技术栈、数据流与渲染机制。重点参考文件：`app/project/.../layout/layout.html`、`internal/js/endcrawl/app/project/layout.js`、`internal/js/endcrawl/common/savequeue.js`、`app/project/.../credits/credits.html` 等。

## 技术栈概览
- **前端框架**：jQuery + Nunjucks（浏览器端模板渲染）
- **样式**：传统 CSS（reset/bootstrap 自定义）、内联 CSS 片段由 Nunjucks 注入
- **模板引擎**：Nunjucks（浏览器端 WebLoader 拉取 `/templates` 下片段；推测服务器端也用 Nunjucks/Jinja 同构）
- **数据模型注入**：服务器端在初始 HTML 中直接注入 `project / site / page` 全量 JSON 变量
- **数据保存**：AJAX（`savequeue.js`）调后端 REST API，传 `csrf_token`
- **协作/实时**：未见 WebSocket，采用前端本地 state + AJAX 刷新
- **外部依赖**：Google Sheets 通过 iframe 直接嵌入（无 Google API SDK 调用）
- **渲染预览**：浏览器内 Nunjucks + DOM 更新；最终片尾渲染后端实现未在仓库内（有渲染占位路由/代理）

## 关键技术原理

### 1) 初始加载：SSR 注入 + CSR 接管
- `layout.html` 中包含大段 `var project = {...}`、`var site = {...}`、`var page = {...}`，由服务器端预先写入 HTML —— **首屏是 SSR（数据注入 + HTML 骨架）**。
- 浏览器加载后，`layout.js` 读取这些全局变量，构造 `model`，然后初始化 `Endcrawl.App.Layout`。
- 之后的所有预览更新走 **CSR**：前端持有 `self.model.project`，用 Nunjucks 在浏览器端渲染局部/整体 DOM。

### 2) 客户端模板渲染（Nunjucks in-browser）
- `layout.js` 中：
  - `self.templater = new nunjucks.Environment(new nunjucks.WebLoader('/templates'), { autoescape: true })`
  - `update_preview()` 使用 `templater.renderString` + 服务器下发的模板片段 `include/credits/*.html` 来生成卡片/块/分隔符/inline css，然后直接替换 DOM。
- 因此 **模板与样式片段在前端复用，避免手写 DOM 拼接**；也暗示服务器端与前端共享同一套模板文件。

### 3) 数据保存与同步
- `savequeue.js`：封装保存队列/防抖，AJAX PUT/POST/DELETE 至 `/api/project/...` 等后端接口，附带 CSRF。
- 交互如切换 block、调整 columns、编辑 cards 都会更新 `self.model.project` 并触发 `update_preview()` 本地预览，然后异步保存。
- “Sync/Reload” 按钮会弹出 modal，之后提交表单到后端刷新数据，再把后端返回的 `project` 替换到前端 model。

### 4) Google Sheets 集成
- 在 `credits.html` 中直接 `<iframe id="gdoc" src="https://docs.google.com/spreadsheets/d/.../edit">`。
- CSS 固定高度/位置；无任何 Google Sheets API 调用。用户在 iframe 内直接编辑 Google 在线表，数据托管在 Google 端，与后端无直接联动。
- 只有当点击 Layout 页的 “Reload/Sync” 时，前端表单提交到后端，由后端去同步最新表数据到项目模型（推测）。

### 5) 渲染路径推测
- 预览：完全在浏览器 DOM + CSS（Nunjucks 生成 HTML 结构）。
- 最终渲染：仓库中未见真实渲染实现；`backend_server.py`/`proxy_server.py` 多为占位或调试路由，渲染可能在实际生产服务端（“supercharged cloud renderer”）完成。

## 数据流（简述）
1) **首屏**：服务器端渲染 HTML，注入 `project/site/page` JSON。
2) **前端初始化**：`layout.js` 读取注入数据 → 建立 model → Nunjucks 预览渲染。
3) **用户编辑**：更新本地 model → `update_preview()` 重新渲染 DOM；并通过 `savequeue.js` 异步保存到后端。
4) **同步表格**：Layout 页点击 Reload → 表单提交后端 → 后端拉取 Google Sheets → 返回新的 project JSON → 前端替换 model 并重渲染。
5) **最终输出**：未在仓库中呈现，推测后端独立渲染服务。

## 判定 CSR / SSR 的依据
- SSR 证据：`layout.html` 直接含完整数据对象；首屏无需额外 API 即可渲染。
- CSR 证据：`layout.js` 在浏览器内用 Nunjucks 反复渲染局部/整体；编辑后即时 DOM 替换。
- 结论：**混合模式** —— 首屏 SSR 注入数据 + CSR 持续渲染与交互。

## 与现代框架的对比
- 当前方案：jQuery + Nunjucks (WebLoader) + 手工 DOM 替换。
- 现代替代：React/Vue + Next/Nuxt 可实现 SSR + Hydration + 组件化，减少双端模板维护，简化状态/DOM 同步。

## 目录指引（与分析相关的主要文件）
- `app/project/.../layout/layout.html`：SSR 注入数据与页面骨架。
- `internal/js/endcrawl/app/project/layout.js`：前端逻辑与 Nunjucks 渲染、事件绑定、刷新/同步。
- `internal/js/endcrawl/common/savequeue.js`：保存队列 + AJAX。
- `app/project/.../credits/credits.html`：Google Sheets iframe 嵌入示例。

## 结论
Endcrawl 采用“服务器端注入初始数据 + 前端 Nunjucks 持续渲染”的混合模式，配合 AJAX 保存与 Google Sheets iframe 直连。预览由前端 DOM 完成，最终渲染未在本仓库呈现，可能由外部后端渲染服务实现。

