"""
滚动长画布渲染引擎（Skia）

用途：
- 将整条字幕渲染在同一超长画布上，用于垂直滚动预览/播放
- 提供按 y 区段（chunk）获取 PNG 图块的能力，便于前端按需加载
- 支持导出序列帧（TIFF 序列），便于前端整体下载

特点：
- 文本渲染沿用 Skia，与最终输出保持一致的排版/抗锯齿效果
- 支持计算总高度，避免“超出画面被裁剪”的问题
- 按区段渲染，方便前端实现虚拟滚动或按时间拉取对应切片
"""
import math
import os
import time
import platform
from typing import Tuple, Optional, List

import numpy as np
import skia
import OpenImageIO as oiio

from app.models import RenderConfig, SubtitleItem, RenderSequenceRequest

# 默认临时目录：项目根目录下的 temp
BASE_TEMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "temp"))
os.makedirs(BASE_TEMP_DIR, exist_ok=True)


class LongScrollRenderEngineSkia:
    """长画布滚动渲染引擎（分块输出 PNG）"""

    def __init__(self):
        self.font_cache = {}
        self._init_default_fonts()

    # ---- 字体管理 ----
    def _init_default_fonts(self):
        """初始化默认字体路径（与 RenderEngineSkia 保持一致逻辑）"""
        system = platform.system()
        if system == "Darwin":  # macOS
            pingfang_paths = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Supplemental/PingFang.ttc",
                "/Library/Fonts/PingFang.ttc",
            ]
            self.default_cn_font = None
            for path in pingfang_paths:
                try:
                    skia.Typeface.MakeFromFile(path)
                    self.default_cn_font = path
                    break
                except:  # noqa: E722
                    continue

            if not self.default_cn_font:
                try:
                    self.default_cn_font = "/System/Library/Fonts/STHeiti Light.ttc"
                    skia.Typeface.MakeFromFile(self.default_cn_font)
                except:  # noqa: E722
                    self.default_cn_font = None

            helvetica_paths = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/HelveticaNeue.ttc",
            ]
            self.default_en_font = None
            for path in helvetica_paths:
                try:
                    skia.Typeface.MakeFromFile(path)
                    self.default_en_font = path
                    break
                except:  # noqa: E722
                    continue
        elif system == "Windows":
            self.default_cn_font = "C:/Windows/Fonts/msyh.ttc"
            self.default_en_font = "C:/Windows/Fonts/arial.ttf"
        else:  # Linux
            self.default_cn_font = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
            self.default_en_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    def get_font(self, font_family: str, font_size: int, is_chinese: bool = False) -> skia.Font:
        """获取 Skia 字体（带缓存）"""
        cache_key = f"{font_family}_{font_size}_{is_chinese}"
        if cache_key not in self.font_cache:
            try:
                typeface = skia.Typeface.MakeFromFile(font_family)
            except:  # noqa: E722
                if is_chinese:
                    if self.default_cn_font:
                        try:
                            typeface = skia.Typeface.MakeFromFile(self.default_cn_font)
                        except:  # noqa: E722
                            typeface = skia.Typeface.MakeDefault()
                    else:
                        typeface = skia.Typeface.MakeDefault()
                else:
                    if self.default_en_font:
                        try:
                            typeface = skia.Typeface.MakeFromFile(self.default_en_font)
                        except:  # noqa: E722
                            typeface = skia.Typeface.MakeDefault()
                    else:
                        typeface = skia.Typeface.MakeDefault()

            font = skia.Font(typeface, font_size)
            self.font_cache[cache_key] = font
        return self.font_cache[cache_key]

    # ---- 公共工具 ----
    def is_chinese_char(self, char: str) -> bool:
        return '\u4e00' <= char <= '\u9fff'

    def calculate_total_height(self, config: RenderConfig, top_padding: int = 0, bottom_padding: int = 0) -> int:
        """
        计算整条字幕在纵向上的总高度，用于创建长画布或决定分块数量
        """
        max_y = 0
        for subtitle in config.subtitles:
            lines = subtitle.text.split("\n")
            line_count = len(lines)
            block_height = 0
            for line in lines:
                if not line.strip():
                    block_height += int(subtitle.font_size * subtitle.line_height)
                    continue
                block_height += int(subtitle.font_size * subtitle.line_height)
            max_y = max(max_y, subtitle.y + block_height)

        return max(config.height, max_y + top_padding + bottom_padding)

    # ---- 渲染入口 ----
    def render_chunk_png(
        self,
        config: RenderConfig,
        y_start: int,
        chunk_height: int,
        total_height: Optional[int] = None,
    ) -> Tuple[bytes, float, int]:
        """
        渲染指定 y 区段的 PNG 切片。

        参数：
        - y_start: 区段起始 y（逻辑坐标，0 顶部）
        - chunk_height: 区段高度
        - total_height: 可选，传入已计算好的总高度，避免重复计算

        返回：
        - png bytes
        - render time (ms)
        - total_height （方便前端了解整条长图高度）
        """
        start_time = time.time()
        total_height = total_height or self.calculate_total_height(config)

        # 如果请求超出范围，返回空白块
        if y_start >= total_height:
            surface = skia.Surface(config.width, chunk_height)
            png_data = surface.makeImageSnapshot().encodeToData(skia.EncodedImageFormat.kPNG, 100)
            return bytes(png_data), (time.time() - start_time) * 1000, total_height

        surface = skia.Surface(config.width, chunk_height)
        canvas = surface.getCanvas()

        # 背景
        canvas.clear(skia.Color(
            config.background_color[0],
            config.background_color[1],
            config.background_color[2],
        ))

        # 将画布上移 y_start，使得只绘制该区段可见部分
        canvas.save()
        canvas.translate(0, -y_start)

        for subtitle in config.subtitles:
            self._render_subtitle(canvas, subtitle, config.width, total_height)

        canvas.restore()

        # 输出 PNG
        image = surface.makeImageSnapshot()
        png_data = image.encodeToData(skia.EncodedImageFormat.kPNG, 100)
        render_time = (time.time() - start_time) * 1000
        return bytes(png_data), render_time, total_height

    def render_tiff_sequence_timebased(
        self,
        req: RenderSequenceRequest,
        output_dir: Optional[str] = None,
    ) -> Tuple[List[str], float, int, int]:
        """
        基于时间轴/FPS 的序列帧渲染：
        - 给定 fps 和 duration_sec 或 scroll_speed(px/s)
        - 每帧 y 偏移 = frameIndex * pixelsPerFrame
        - 帧尺寸固定：width=config.width, height=config.height
        返回：帧路径列表、耗时 ms、总高度、总帧数
        """
        start_time = time.time()
        config = req.config
        target_dir = output_dir or BASE_TEMP_DIR
        os.makedirs(target_dir, exist_ok=True)

        total_height = self.calculate_total_height(config)
        scroll_pixels = max(0, total_height - config.height)

        fps = max(1e-3, req.fps)

        # 计算总帧数与每帧位移
        if req.duration_sec and req.duration_sec > 0:
            total_frames = max(1, math.ceil(fps * req.duration_sec))
            pixels_per_frame = scroll_pixels / total_frames if total_frames > 0 else 0
        elif req.scroll_speed and req.scroll_speed > 0:
            pixels_per_frame = req.scroll_speed / fps
            total_frames = max(1, math.ceil(scroll_pixels / pixels_per_frame)) if pixels_per_frame > 0 else 1
        else:
            # fallback：与旧逻辑一致，按帧高切分
            total_frames = max(1, math.ceil(total_height / config.height))
            pixels_per_frame = scroll_pixels / total_frames if total_frames > 0 else 0

        frame_paths: List[str] = []

        for idx in range(total_frames):
            y_start = min(scroll_pixels, idx * pixels_per_frame)

            surface = skia.Surface(config.width, config.height)
            canvas = surface.getCanvas()

            canvas.clear(skia.Color(
                config.background_color[0],
                config.background_color[1],
                config.background_color[2],
            ))

            canvas.save()
            canvas.translate(0, -y_start)

            for subtitle in config.subtitles:
                self._render_subtitle(canvas, subtitle, config.width, total_height)

            canvas.restore()

            image = surface.makeImageSnapshot()
            pixels = image.tobytes()
            img_array = np.frombuffer(pixels, dtype=np.uint8)
            img_array = img_array.reshape((config.height, config.width, 4))  # RGBA
            img_array = img_array[:, :, :3]  # RGB

            frame_name = f"frame_{idx:05d}.tiff"
            frame_path = os.path.join(target_dir, frame_name)

            spec = oiio.ImageSpec(config.width, config.height, 3, oiio.UINT8)
            buf = oiio.ImageBuf(spec)
            buf.set_pixels(oiio.ROI(0, config.width, 0, config.height, 0, 1, 0, 3), img_array)
            buf.write(frame_path)

            frame_paths.append(frame_path)

        render_time = (time.time() - start_time) * 1000
        return frame_paths, render_time, total_height, total_frames

    def render_full_png(self, config: RenderConfig) -> Tuple[bytes, float, int]:
        """
        渲染完整长图（全分辨率）
        返回：PNG bytes, 渲染时间 ms, 总高度
        """
        start_time = time.time()
        total_height = self.calculate_total_height(config)

        surface = skia.Surface(config.width, total_height)
        canvas = surface.getCanvas()

        canvas.clear(skia.Color(
            config.background_color[0],
            config.background_color[1],
            config.background_color[2],
        ))

        for subtitle in config.subtitles:
            self._render_subtitle(canvas, subtitle, config.width, total_height)

        image = surface.makeImageSnapshot()
        png_data = image.encodeToData(skia.EncodedImageFormat.kPNG, 100)
        render_time = (time.time() - start_time) * 1000
        return bytes(png_data), render_time, total_height

    def render_tiff_sequence(
        self,
        config: RenderConfig,
        output_dir: Optional[str] = None,
    ) -> Tuple[List[str], float, int]:
        """
        渲染序列帧式的 TIFF 序列（固定帧高为 config.height）
        - 按画面高度切分长图，逐帧输出 TIFF
        - 帧大小保持一致：宽=config.width，高=config.height
        - 输出路径列表、总耗时 ms、总高度
        """
        start_time = time.time()
        total_height = self.calculate_total_height(config)
        target_dir = output_dir or BASE_TEMP_DIR
        os.makedirs(target_dir, exist_ok=True)

        frame_paths: List[str] = []
        frame_count = max(1, math.ceil(total_height / config.height))

        for idx in range(frame_count):
            y_start = idx * config.height

            # 以固定分辨率创建帧画布
            surface = skia.Surface(config.width, config.height)
            canvas = surface.getCanvas()

            # 清背景
            canvas.clear(skia.Color(
                config.background_color[0],
                config.background_color[1],
                config.background_color[2],
            ))

            # 将画布上移 y_start，使得当前帧呈现该窗口内容
            canvas.save()
            canvas.translate(0, -y_start)

            for subtitle in config.subtitles:
                self._render_subtitle(canvas, subtitle, config.width, total_height)

            canvas.restore()

            # 获取像素并用 OIIO 输出 TIFF
            image = surface.makeImageSnapshot()
            pixels = image.tobytes()
            img_array = np.frombuffer(pixels, dtype=np.uint8)
            img_array = img_array.reshape((config.height, config.width, 4))  # RGBA
            img_array = img_array[:, :, :3]  # RGB

            frame_name = f"frame_{idx:05d}.tiff"
            frame_path = os.path.join(target_dir, frame_name)

            spec = oiio.ImageSpec(config.width, config.height, 3, oiio.UINT8)
            buf = oiio.ImageBuf(spec)
            buf.set_pixels(oiio.ROI(0, config.width, 0, config.height, 0, 1, 0, 3), img_array)
            buf.write(frame_path)

            frame_paths.append(frame_path)

        render_time = (time.time() - start_time) * 1000
        return frame_paths, render_time, total_height

    # ---- 核心绘制 ----
    def _render_subtitle(self, canvas: skia.Canvas, subtitle: SubtitleItem,
                         canvas_width: int, canvas_height: int):
        """
        渲染单个字幕；逻辑与 RenderEngineSkia 保持一致，支持中英文字体分离与字距。
        """
        paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
        )

        paint.setColor(skia.Color(
            subtitle.color[0],
            subtitle.color[1],
            subtitle.color[2],
        ))

        lines = subtitle.text.split('\n')
        y_offset = subtitle.y

        for line in lines:
            if not line.strip():
                y_offset += int(subtitle.font_size * subtitle.line_height)
                continue

            if subtitle.letter_spacing != 0:
                x_offset = subtitle.x
                for char in line:
                    is_cn = self.is_chinese_char(char)
                    if is_cn and subtitle.font_family_cn:
                        font = self.get_font(subtitle.font_family_cn, subtitle.font_size, is_chinese=True)
                    else:
                        font = self.get_font(subtitle.font_family, subtitle.font_size, is_chinese=False)

                    canvas.drawString(char, x_offset, y_offset, font, paint)

                    char_width = font.measureText(char)
                    x_offset += char_width + subtitle.letter_spacing
            else:
                x_offset = subtitle.x
                current_segment = ""
                current_is_cn = None

                for char in line:
                    is_cn = self.is_chinese_char(char)

                    if current_is_cn is not None and is_cn != current_is_cn:
                        if current_segment:
                            font = self.get_font(
                                subtitle.font_family_cn if current_is_cn else subtitle.font_family,
                                subtitle.font_size,
                                is_chinese=current_is_cn,
                            )
                            canvas.drawString(current_segment, x_offset, y_offset, font, paint)
                            segment_width = font.measureText(current_segment)
                            x_offset += segment_width
                        current_segment = ""

                    current_segment += char
                    current_is_cn = is_cn

                if current_segment:
                    font = self.get_font(
                        subtitle.font_family_cn if current_is_cn else subtitle.font_family,
                        subtitle.font_size,
                        is_chinese=current_is_cn if current_is_cn is not None else False,
                    )
                    canvas.drawString(current_segment, x_offset, y_offset, font, paint)

            y_offset += int(subtitle.font_size * subtitle.line_height)

