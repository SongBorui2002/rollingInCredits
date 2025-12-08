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


class PreviewResponse(BaseModel):
    """预览响应"""
    preview_url: str
    render_time_ms: float

