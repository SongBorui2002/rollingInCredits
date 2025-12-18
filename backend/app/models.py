from pydantic import BaseModel
from typing import List, Optional, Tuple


class SubtitleItem(BaseModel):
    """字幕项"""
    id: str
    text: str
    x: int
    y: int
    font_family: str = "Arial"  # 英文字体
    font_family_cn: Optional[str] = None  # 中文字体（可选，如果为None则使用font_family）
    font_size: int = 48
    letter_spacing: float = 0.0  # 字间距（像素）
    line_height: float = 1.2  # 行间距（倍数）
    color: Tuple[int, int, int] = (255, 255, 255)  # RGB


class RenderConfig(BaseModel):
    """渲染配置"""
    width: int = 3840
    height: int = 2160
    subtitles: List[SubtitleItem]
    background_color: Tuple[int, int, int] = (0, 0, 0)  # RGB
    preview: bool = False  # 是否为预览模式
    preview_scale: float = 1.0  # 预览模式下的分辨率缩放
    ensure_no_scroll: Optional[bool] = False  # 确保没有抖动（开启 Baseline Snapping 和 Hinting）
    optimization_mode: Optional[str] = None  # 优化模式，'duration' 时长优先，'layout' 排版优先


class PreviewResponse(BaseModel):
    """预览响应"""
    preview_url: str
    render_time_ms: float


class ScrollPreviewRequest(BaseModel):
    """滚动预览请求：指定区段获取全分辨率切片"""
    config: RenderConfig
    y_start: int
    chunk_height: int


class ScrollPreviewResponse(BaseModel):
    """滚动预览响应：返回区段 PNG 及总高度信息"""
    preview_url: str
    render_time_ms: float
    total_height: int
    y_start: int
    chunk_height: int


class ScrollFullPreviewResponse(BaseModel):
    """完整长图预览响应"""
    preview_url: str
    render_time_ms: float
    total_height: int


class RenderSequenceRequest(BaseModel):
    """
    逐帧渲染请求：
    - fps: 目标帧率
    - duration_sec: 总时长（秒），与 scroll_speed 二选一，优先使用 duration
    - scroll_speed: 滚动速度（px/s），当未提供 duration 时使用
    - ensure_no_scroll: 确保没有滚动（开启 Baseline Snapping 和 Hinting）
    - optimization_mode: 优化模式，'duration' 时长优先，'layout' 排版优先
    """
    config: RenderConfig
    fps: float = 24.0
    duration_sec: Optional[float] = None
    scroll_speed: Optional[float] = None
    ensure_no_scroll: Optional[bool] = False
    optimization_mode: Optional[str] = None  # 'duration' or 'layout'
