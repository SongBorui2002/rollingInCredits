"""
FastAPI 后端主文件 - Skia 版本
使用 Skia 渲染引擎替代 Pillow
"""
import base64
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse

from app.models import RenderConfig, PreviewResponse
from app.render_engine_skia import RenderEngineSkia

app = FastAPI(title="RollingInCredits API (Skia)")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 Skia 渲染引擎
render_engine = RenderEngineSkia()


@app.get("/")
async def root():
    return {"message": "RollingInCredits API (Skia)", "engine": "Skia"}


@app.post("/api/preview", response_model=PreviewResponse)
async def get_preview(config: RenderConfig):
    """
    获取预览图像
    返回 PNG 格式的 base64 编码图像
    """
    try:
        # 使用 Skia 渲染引擎
        preview_data, render_time = render_engine.render_preview(config)
        
        # 转换为 base64
        preview_base64 = base64.b64encode(preview_data).decode('utf-8')
        preview_url = f"data:image/png;base64,{preview_base64}"
        
        return PreviewResponse(
            preview_url=preview_url,
            render_time_ms=render_time
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/render/dpx")
async def render_dpx(config: RenderConfig):
    """
    渲染最终 DPX 文件
    返回 DPX 格式的文件
    """
    try:
        dpx_data, render_time = render_engine.render_final_dpx(config)
        
        return Response(
            content=dpx_data,
            media_type="image/x-dpx",  # DPX 格式的 MIME 类型
            headers={
                "Content-Disposition": "attachment; filename=output.dpx",
                "X-Render-Time-Ms": str(render_time)
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/render/tiff")
async def render_tiff(config: RenderConfig):
    """
    渲染最终 TIFF 文件
    返回 TIFF 格式的文件
    """
    try:
        tiff_data, render_time = render_engine.render_final_tiff(config)
        
        return Response(
            content=tiff_data,
            media_type="image/tiff",  # TIFF 格式的 MIME 类型
            headers={
                "Content-Disposition": "attachment; filename=output.tiff",
                "X-Render-Time-Ms": str(render_time)
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok", "engine": "Skia"}

