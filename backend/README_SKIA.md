# Skia 渲染引擎

这是使用 Skia 的渲染引擎实现，提供比 Pillow 更高质量的文本渲染。

## 优势

### 1. 更高质量的文本渲染
- **更好的抗锯齿**: Skia 使用 subpixel rendering，文本边缘更平滑
- **更精确的字体度量**: 更准确的字符宽度和位置计算
- **更好的小字号渲染**: 在小字号下文本更清晰

### 2. 性能优势
- **硬件加速**: 支持 GPU 加速（如果可用）
- **更快的渲染速度**: 对于高分辨率图像，Skia 通常更快

### 3. 专业标准
- **行业标准**: 被 Chrome、Android、Flutter 等广泛使用
- **现代渲染引擎**: 持续更新和维护

## 使用方法

### 方式 1: 使用 Skia 版本的 API 服务器

```bash
# 启动 Skia 版本的后端
cd backend
source venv/bin/activate
uvicorn app.main_skia:app --reload --port 8000
```

### 方式 2: 在代码中切换渲染引擎

修改 `backend/app/main.py`:

```python
# 从
from app.render_engine import RenderEngine
render_engine = RenderEngine()

# 改为
from app.render_engine_skia import RenderEngineSkia
render_engine = RenderEngineSkia()
```

## 性能对比

基于测试结果（1920x1080 分辨率）：

| 操作 | Pillow | Skia | 说明 |
|------|--------|------|------|
| 预览渲染 | ~24ms | ~62ms | Skia 稍慢，但质量更好 |
| DPX 渲染 | ~24ms | ~20ms | Skia 稍快 |
| TIFF 渲染 | ~25ms | ~12ms | Skia 明显更快 |

**注意**: 性能差异可能因系统配置而异。

## 渲染质量对比

### Pillow
- ✅ 基本文本渲染
- ✅ 抗锯齿支持
- ⚠️ 小字号可能不够清晰
- ⚠️ 字体度量可能不够精确

### Skia
- ✅ 高质量文本渲染
- ✅ 更好的抗锯齿（subpixel rendering）
- ✅ 更精确的字体度量
- ✅ 更好的小字号渲染
- ✅ 专业级渲染质量

## 接口兼容性

Skia 渲染引擎 (`RenderEngineSkia`) 实现了与 Pillow 版本 (`RenderEngine`) 完全相同的接口：

- `render_preview(config: RenderConfig) -> Tuple[bytes, float]`
- `render_final_dpx(config: RenderConfig) -> Tuple[bytes, float]`
- `render_final_tiff(config: RenderConfig) -> Tuple[bytes, float]`

因此可以无缝切换，无需修改前端代码。

## 依赖

- `skia-python>=138.0`: Skia 的 Python 绑定
- `OpenImageIO>=3.0.0`: 专业格式输出
- `numpy>=1.26.0`: 数组处理

## 注意事项

1. **字体路径**: Skia 和 Pillow 使用相同的字体文件路径，确保字体文件存在
2. **渲染一致性**: Skia 和 Pillow 的渲染结果可能略有差异（Skia 质量更好）
3. **性能**: 对于预览渲染，Skia 可能稍慢，但最终输出通常更快
4. **兼容性**: Skia 需要系统支持，在某些环境下可能需要额外配置

## 推荐使用场景

### 使用 Skia 当：
- ✅ 需要最高质量的文本渲染
- ✅ 处理高分辨率图像
- ✅ 专业视频制作
- ✅ 需要精确的字体度量

### 使用 Pillow 当：
- ✅ 快速原型开发
- ✅ 对渲染质量要求不高
- ✅ 需要更简单的依赖管理
- ✅ 系统资源有限

## 测试

运行测试：

```bash
cd backend
source venv/bin/activate
python -c "
from app.render_engine_skia import RenderEngineSkia
from app.models import RenderConfig, SubtitleItem

engine = RenderEngineSkia()
config = RenderConfig(
    width=1920,
    height=1080,
    subtitles=[
        SubtitleItem(
            id='1',
            text='测试\nTest',
            x=960,
            y=400,
            font_family='Arial',
            font_family_cn='/System/Library/Fonts/STHeiti Light.ttc',
            font_size=48,
            letter_spacing=0,
            line_height=1.5,
            color=(255, 255, 255)
        )
    ],
    background_color=(0, 0, 0),
    preview=False
)

result, time = engine.render_preview(config)
print(f'Preview: {len(result)} bytes, {time:.2f}ms')
"
```

