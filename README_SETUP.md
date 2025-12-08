# 快速开始

这是一个用于测试前后端渲染一致性的简单项目。

## 安装步骤

### 1. 后端设置

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 前端设置

```bash
cd frontend
npm install
```

## 运行

### 启动后端

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

后端将在 `http://localhost:8000` 运行

### 启动前端

```bash
cd frontend
npm run dev
```

前端将在 `http://localhost:5173` 运行

## 使用说明

1. 打开浏览器访问 `http://localhost:5173`
2. 在右侧控制面板编辑字幕属性：
   - 文本内容
   - 位置 (X, Y)
   - 字体
   - 字号
   - 字间距
   - 行间距
   - 颜色 (RGB)
3. 预览图像会实时更新（防抖 300ms）
4. 点击"渲染 DPX"按钮下载最终渲染文件

## 测试要点

### 渲染一致性测试
- 调整字体、字号、字间距、行间距
- 观察预览图像与最终渲染是否一致
- 检查文本位置、大小、间距是否准确

### 延迟测试
- 观察编辑后到预览更新的延迟时间
- 查看渲染时间显示（毫秒）
- 测试不同分辨率下的渲染性能

## 注意事项

1. **字体文件**: 当前使用系统字体，如需特定字体，请确保系统已安装
2. **DPX 格式**: 
   - 当前版本使用 Pillow 进行渲染，输出为 TIFF 格式（作为 DPX 的替代）
   - 这是为了快速测试前后端通信和渲染一致性
   - 实际生产环境应使用 OpenImageIO (OIIO) 进行真正的 DPX 渲染
   - 预览和最终渲染使用相同的渲染逻辑，确保一致性
3. **预览分辨率**: 预览使用与配置相同的分辨率，可通过修改代码降低预览分辨率以提升性能
4. **渲染一致性**: 
   - ✅ 前端 Canvas 只用于交互层（选择框、拖拽手柄），不渲染字幕文本
   - ✅ 所有字幕文本由后端统一渲染
   - ✅ 预览和最终渲染使用相同的渲染函数 `_render_subtitle()`
   - ✅ 确保字体、字号、字间距、行间距与最终输出完全一致

## 下一步

- 集成 OIIO 进行真正的 DPX 渲染
- 添加字体文件上传功能
- 实现更精确的文本度量
- 添加缓存机制减少延迟
- 实现 WebSocket 实时预览

