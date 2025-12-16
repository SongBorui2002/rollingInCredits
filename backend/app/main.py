"""
FastAPI 后端主文件
"""
import base64
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse

from app.models import (
    RenderConfig,
    PreviewResponse,
    ScrollPreviewRequest,
    ScrollPreviewResponse,
    ScrollFullPreviewResponse,
    RenderSequenceRequest,
)
# 使用 Skia 渲染引擎（更高质量的文本渲染）
from app.render_engine_skia import RenderEngineSkia
from app.render_engine_scroll import LongScrollRenderEngineSkia
import tempfile
import zipfile
import os

# 固定临时目录：项目根目录下 temp
BASE_TEMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "temp"))
os.makedirs(BASE_TEMP_DIR, exist_ok=True)
# 如果需要使用 Pillow 版本，取消下面的注释并注释掉上面的导入
# from app.render_engine import RenderEngine

app = FastAPI(title="RollingInCredits API (Skia)")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化渲染引擎（使用 Skia 版本，提供更高质量的文本渲染）
render_engine = RenderEngineSkia()
scroll_engine = LongScrollRenderEngineSkia()
# 如果使用 Pillow 版本，改为：
# render_engine = RenderEngine()


@app.get("/")
async def root():
    return {"message": "RollingInCredits API", "engine": "Skia"}


@app.post("/api/preview", response_model=PreviewResponse)
async def get_preview(config: RenderConfig):
    """
    获取预览图像
    返回 PNG 格式的 base64 编码图像
    """
    try:
        # 使用统一的渲染引擎
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
    return {"status": "ok"}


@app.post("/api/preview/scroll-chunk", response_model=ScrollPreviewResponse)
async def get_scroll_chunk(payload: ScrollPreviewRequest):
    """
    获取全分辨率滚动预览的区段 PNG
    """
    try:
        png_data, render_time, total_height = scroll_engine.render_chunk_png(
            config=payload.config,
            y_start=payload.y_start,
            chunk_height=payload.chunk_height,
            total_height=None,
        )
        preview_base64 = base64.b64encode(png_data).decode("utf-8")
        preview_url = f"data:image/png;base64,{preview_base64}"
        return ScrollPreviewResponse(
            preview_url=preview_url,
            render_time_ms=render_time,
            total_height=total_height,
            y_start=payload.y_start,
            chunk_height=payload.chunk_height,
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.post("/api/preview/scroll-full", response_model=ScrollFullPreviewResponse)
async def get_scroll_full(config: RenderConfig):
    """
    获取全分辨率长图（一次性渲染，不做分块），用于前端本地滚动预览
    """
    try:
        png_data, render_time, total_height = scroll_engine.render_full_png(config)
        preview_base64 = base64.b64encode(png_data).decode("utf-8")
        preview_url = f"data:image/png;base64,{preview_base64}"
        return ScrollFullPreviewResponse(
            preview_url=preview_url,
            render_time_ms=render_time,
            total_height=total_height,
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.post("/api/render/tiff-seq")
async def render_tiff_sequence(config: RenderConfig):
    """
    渲染长画布为 TIFF 序列并打包 ZIP 返回
    """
    try:
        with tempfile.TemporaryDirectory(dir=BASE_TEMP_DIR) as tmpdir:
            frame_paths, render_time, total_height = scroll_engine.render_tiff_sequence(
                config=config,
                output_dir=tmpdir,
            )

            zip_path = os.path.join(tmpdir, "tiff_sequence.zip")
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for p in frame_paths:
                    zf.write(p, arcname=os.path.basename(p))

            with open(zip_path, "rb") as f:
                data = f.read()

            return Response(
                content=data,
                media_type="application/zip",
                headers={
                    "Content-Disposition": "attachment; filename=tiff_sequence.zip",
                    "X-Render-Time-Ms": str(render_time),
                    "X-Total-Height": str(total_height),
                    "X-Frame-Count": str(len(frame_paths)),
                },
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.post("/api/render/tiff-seq-fps")
async def render_tiff_sequence_fps(req: RenderSequenceRequest):
    """
    基于 FPS/时长/速度 的逐帧渲染，输出 TIFF 序列 ZIP
    """
    try:
        with tempfile.TemporaryDirectory(dir=BASE_TEMP_DIR) as tmpdir:
            frame_paths, render_time, total_height, total_frames = scroll_engine.render_tiff_sequence_timebased(
                req=req,
                output_dir=tmpdir,
            )

            zip_path = os.path.join(tmpdir, "tiff_sequence.zip")
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for p in frame_paths:
                    zf.write(p, arcname=os.path.basename(p))

            with open(zip_path, "rb") as f:
                data = f.read()

            return Response(
                content=data,
                media_type="application/zip",
                headers={
                    "Content-Disposition": "attachment; filename=tiff_sequence.zip",
                    "X-Render-Time-Ms": str(render_time),
                    "X-Total-Height": str(total_height),
                    "X-Frame-Count": str(len(frame_paths)),
                    "X-Fps": str(req.fps),
                    "X-Total-Frames": str(total_frames),
                },
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )

