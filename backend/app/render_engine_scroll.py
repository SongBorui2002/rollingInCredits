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
        # 字体渲染配置（用于"确保没有滚动"模式）
        self.enable_baseline_snap = False
        self.enable_hinting = False

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
        """获取 Skia 字体（带缓存），根据配置启用/禁用 Baseline Snapping 和 Hinting"""
        # 将字体配置也加入缓存键，因为不同配置需要不同的字体对象
        cache_key = f"{font_family}_{font_size}_{is_chinese}_{self.enable_baseline_snap}_{self.enable_hinting}"
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

            # 根据配置设置字体属性
            try:
                # 1) 基线对齐（Y 轴 snap）- 根据配置开启/关闭
                if hasattr(font, "setBaselineSnap"):
                    font.setBaselineSnap(self.enable_baseline_snap)

                # 2) 使用标准灰阶抗锯齿（不能用 LCD 子像素）
                if hasattr(font, "setEdging") and hasattr(skia.Font, "Edging"):
                    font.setEdging(skia.Font.Edging.kAntiAlias)

                # 3) Hinting - 根据配置开启/关闭
                if hasattr(font, "setHinting"):
                    if self.enable_hinting:
                        # 开启 hinting
                        if hasattr(skia, "FontHinting"):
                            font.setHinting(skia.FontHinting.kNormal)
                        elif hasattr(skia.Font, "kNormal_Hinting"):
                            font.setHinting(skia.Font.kNormal_Hinting)
                    else:
                        # 禁用 hinting
                        if hasattr(skia, "FontHinting"):
                            font.setHinting(skia.FontHinting.kNone)
                        elif hasattr(skia.Font, "kNo_Hinting"):
                            font.setHinting(skia.Font.kNo_Hinting)

                # 4) 启用线性度量
                if hasattr(font, "setLinearMetrics"):
                    font.setLinearMetrics(True)

                # 5) 启用亚像素定位
                if hasattr(font, "setSubpixel"):
                    font.setSubpixel(True)
            except (AttributeError, TypeError):
                # 如果 API 不支持，继续使用默认设置
                pass
            
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
        
        # 保存原始配置，以便后续恢复
        original_baseline_snap = self.enable_baseline_snap
        original_hinting = self.enable_hinting
        
        # 如果启用"确保没有抖动"，开启 Baseline Snapping 和 Hinting
        if config.ensure_no_scroll:
            self.enable_baseline_snap = True
            self.enable_hinting = True
            # 清空字体缓存，因为配置改变了
            self.font_cache.clear()
        else:
            self.enable_baseline_snap = False
            self.enable_hinting = False
        
        try:
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
        finally:
            # 恢复原始字体配置
            self.enable_baseline_snap = original_baseline_snap
            self.enable_hinting = original_hinting
            self.font_cache.clear()

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
        - 支持"确保没有滚动"模式：开启 Baseline Snapping 和 Hinting，并取整 px/frame
        返回：帧路径列表、耗时 ms、总高度、总帧数
        """
        start_time = time.time()
        config = req.config
        target_dir = output_dir or BASE_TEMP_DIR
        os.makedirs(target_dir, exist_ok=True)

        # 保存原始配置，以便后续恢复
        original_baseline_snap = self.enable_baseline_snap
        original_hinting = self.enable_hinting
        
        # 如果启用"确保没有滚动"，开启 Baseline Snapping 和 Hinting
        if req.ensure_no_scroll:
            self.enable_baseline_snap = True
            self.enable_hinting = True
            # 清空字体缓存，因为配置改变了
            self.font_cache.clear()
        else:
            self.enable_baseline_snap = False
            self.enable_hinting = False

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

        # 如果启用"确保没有抖动"，进行取整处理
        original_pixels_per_frame = pixels_per_frame
        original_total_frames = total_frames
        original_total_height = total_height
        original_scroll_pixels = scroll_pixels
        adjusted_config = config
        
        if req.ensure_no_scroll and req.optimization_mode:
            # 取整处理：确保至少为 1px/frame，避免为 0
            pixels_per_frame_rounded = max(1, round(pixels_per_frame))
            
            print(f"[优化] 原始 px/frame={original_pixels_per_frame:.6f}, 取整后={pixels_per_frame_rounded}")
            
            if req.optimization_mode == 'layout':
                # 排版优先：直接取整，重新计算总帧数
                pixels_per_frame = pixels_per_frame_rounded
                if pixels_per_frame > 0:
                    total_frames = max(1, math.ceil(scroll_pixels / pixels_per_frame))
                    # 重新计算实际的 scroll_pixels，确保最后一帧能完整显示
                    scroll_pixels = (total_frames - 1) * pixels_per_frame
                else:
                    total_frames = 1
                    pixels_per_frame = 0
                
                print(f"[优化-排版优先] px/frame={pixels_per_frame}, 总帧数={total_frames}, scroll_pixels={scroll_pixels}")
                
            elif req.optimization_mode == 'duration':
                # 时长优先：取整但保持总帧数不变，通过调整行间距补偿
                pixels_per_frame = pixels_per_frame_rounded
                
                # 计算目标总滚动距离
                target_total_scroll = pixels_per_frame * total_frames
                # 计算需要调整的滚动距离差异
                scroll_diff = target_total_scroll - original_scroll_pixels
                
                print(f"[优化-时长优先] 原始 scroll_pixels={original_scroll_pixels:.2f}, "
                      f"目标 scroll_pixels={target_total_scroll:.2f}, 差异={scroll_diff:.2f}px")
                
                if abs(scroll_diff) > 0.01:  # 如果差异足够大才调整
                    # 计算新的目标总高度
                    target_total_height = original_total_height + scroll_diff
                    
                    # 计算所有字幕块的总高度（不包括空白区域）
                    total_subtitle_height = 0
                    for subtitle in config.subtitles:
                        lines = subtitle.text.split("\n")
                        block_height = 0
                        for line in lines:
                            if line.strip():
                                block_height += subtitle.font_size * subtitle.line_height
                        # 计算这个字幕块的底部位置
                        subtitle_bottom = subtitle.y + block_height
                        total_subtitle_height = max(total_subtitle_height, subtitle_bottom)
                    
                    # 计算可调整的行间距总高度（字幕内容部分）
                    # 原始字幕内容高度 = total_subtitle_height
                    # 原始总高度 = original_total_height
                    # 需要增加的高度 = scroll_diff
                    
                    if total_subtitle_height > 0:
                        # 计算调整比例：新高度 / 原高度
                        height_ratio = (total_subtitle_height + scroll_diff) / total_subtitle_height if total_subtitle_height > 0 else 1.0
                        
                        # 确保比例合理（不能太小或太大）
                        height_ratio = max(0.5, min(2.0, height_ratio))
                        
                        # 创建调整后的配置副本
                        from copy import deepcopy
                        adjusted_config = deepcopy(config)
                        
                        # 按比例调整所有字幕的行间距
                        for subtitle in adjusted_config.subtitles:
                            subtitle.line_height = subtitle.line_height * height_ratio
                        
                        # 重新计算总高度
                        total_height = self.calculate_total_height(adjusted_config)
                        scroll_pixels = max(0, total_height - config.height)
                        
                        # 验证：确保新的 scroll_pixels 接近目标值
                        actual_scroll_diff = scroll_pixels - original_scroll_pixels
                        print(f"[优化-时长优先] 行间距调整比例={height_ratio:.4f}, "
                              f"新总高度={total_height:.2f}, 新 scroll_pixels={scroll_pixels:.2f}, "
                              f"实际差异={actual_scroll_diff:.2f}px")
                    else:
                        print(f"[优化-时长优先] 警告：无法计算字幕高度，跳过行间距调整")
                else:
                    print(f"[优化-时长优先] 差异太小，无需调整行间距")

        try:
            frame_paths: List[str] = []
            prev_img: Optional[np.ndarray] = None
            prev_y_start: Optional[int] = None

            print(f"[渲染开始] 总帧数={total_frames}, px/frame={pixels_per_frame:.4f}, scroll_pixels={scroll_pixels:.2f}")

            for idx in range(total_frames):
                # 计算当前帧的 y_start，确保是整数像素（避免亚像素偏移导致重复帧）
                y_start_float = idx * pixels_per_frame
                y_start = int(round(y_start_float))
                y_start = min(int(scroll_pixels), y_start)  # 确保不超过最大滚动距离
                
                # 确保每帧的 y_start 至少比前一帧大 1 像素（如果可能）
                if idx > 0 and prev_y_start is not None:
                    if y_start <= prev_y_start:
                        y_start = prev_y_start + 1
                        y_start = min(int(scroll_pixels), y_start)
                        if y_start > scroll_pixels:
                            # 如果已经到达底部，停止渲染
                            print(f"[渲染] 警告：Frame {idx} 已到达底部，停止渲染")
                            break
                
                # 调试信息（前5帧和最后1帧）
                if idx < 5 or idx == total_frames - 1 or (idx % 100 == 0):
                    print(f"[渲染] Frame {idx}: y_start={y_start} (px/frame={pixels_per_frame:.4f}, 计算值={y_start_float:.4f})")

                surface = skia.Surface(config.width, config.height)
                canvas = surface.getCanvas()

                canvas.clear(skia.Color(
                    config.background_color[0],
                    config.background_color[1],
                    config.background_color[2],
                ))

                canvas.save()
                canvas.translate(0, -float(y_start))  # 使用浮点数以确保精度

                # # 验证变换矩阵
                # matrix = canvas.getTotalMatrix()
                # print(f"Frame {idx}: y_start={y_start}, matrix ty={matrix.getTranslateY()}")

                for subtitle in adjusted_config.subtitles:
                    self._render_subtitle(canvas, subtitle, config.width, total_height)

                canvas.restore()

                image = surface.makeImageSnapshot()
                pixels = image.tobytes()
                img_array = np.frombuffer(pixels, dtype=np.uint8)
                img_array = img_array.reshape((config.height, config.width, 4))  # RGBA
                img_array = img_array[:, :, :3]  # RGB

                # 调试：比较相邻两帧的像素差异，确认是否存在完全相同的帧
                if prev_img is not None and prev_y_start is not None:
                    # 使用 int16 防止减法溢出
                    diff = np.abs(img_array.astype(np.int16) - prev_img.astype(np.int16))
                    max_diff = int(diff.max())
                    y_diff = y_start - prev_y_start
                    
                    # 只在有差异或前几帧时打印
                    if max_diff == 0 or idx < 5:
                        print(
                            f"[帧差异] Frame {idx-1}->{idx}: "
                            f"y_start_prev={prev_y_start}, y_start_curr={y_start}, y_diff={y_diff}, "
                            f"max_rgb_diff={max_diff}"
                        )
                        if max_diff == 0 and y_diff > 0:
                            print(f"[警告] Frame {idx-1} 和 {idx} 完全相同，但 y_start 不同！")
                prev_img = img_array.copy()
                prev_y_start = y_start

                frame_name = f"frame_{idx:05d}.tiff"
                frame_path = os.path.join(target_dir, frame_name)

                spec = oiio.ImageSpec(config.width, config.height, 3, oiio.UINT8)
                buf = oiio.ImageBuf(spec)
                buf.set_pixels(oiio.ROI(0, config.width, 0, config.height, 0, 1, 0, 3), img_array)
                buf.write(frame_path)

                frame_paths.append(frame_path)

            render_time = (time.time() - start_time) * 1000
            
            return frame_paths, render_time, total_height, total_frames
        finally:
            # 恢复原始字体配置（无论成功还是异常）
            self.enable_baseline_snap = original_baseline_snap
            self.enable_hinting = original_hinting
            # 清空字体缓存，恢复默认配置
            self.font_cache.clear()

    def render_full_png(self, config: RenderConfig) -> Tuple[bytes, float, int]:
        """
        渲染完整长图（全分辨率）
        返回：PNG bytes, 渲染时间 ms, 总高度
        """
        start_time = time.time()
        
        # 保存原始配置，以便后续恢复
        original_baseline_snap = self.enable_baseline_snap
        original_hinting = self.enable_hinting
        
        # 如果启用"确保没有抖动"，开启 Baseline Snapping 和 Hinting
        if config.ensure_no_scroll:
            self.enable_baseline_snap = True
            self.enable_hinting = True
            # 清空字体缓存，因为配置改变了
            self.font_cache.clear()
        else:
            self.enable_baseline_snap = False
            self.enable_hinting = False
        
        try:
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
        finally:
            # 恢复原始字体配置
            self.enable_baseline_snap = original_baseline_snap
            self.enable_hinting = original_hinting
            self.font_cache.clear()

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
        注意：保持浮点坐标精度，禁用 hinting 以避免像素对齐导致的重复帧问题。
        """
        paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
        )

        # 禁用字体 hinting，启用亚像素文本渲染，确保亚像素偏移能正确渲染
        # 这可以防止文本被对齐到整数像素，导致 0.5px/frame 时出现重复帧
        try:
            # 禁用 Paint 层面的 hinting
            if hasattr(skia.Paint, 'kNo_Hinting'):
                paint.setHinting(skia.Paint.kNo_Hinting)
            elif hasattr(skia, 'PaintHinting'):
                paint.setHinting(skia.PaintHinting.kNone)
            
            # 启用亚像素文本渲染
            if hasattr(paint, 'setSubpixelText'):
                paint.setSubpixelText(True)
            # 禁用 LCD 子像素渲染（可能影响对齐）
            if hasattr(paint, 'setLCDRenderText'):
                paint.setLCDRenderText(False)
        except (AttributeError, TypeError):
            # 如果 API 不支持，继续使用默认设置
            pass

        paint.setColor(skia.Color(
            subtitle.color[0],
            subtitle.color[1],
            subtitle.color[2],
        ))

        lines = subtitle.text.split('\n')
        # 保持 y_offset 为浮点数，不要强制取整
        y_offset = float(subtitle.y)
        line_height = float(subtitle.font_size * subtitle.line_height)

        for line in lines:
            if not line.strip():
                y_offset += line_height
                continue

            if subtitle.letter_spacing != 0:
                x_offset = float(subtitle.x)
                for char in line:
                    is_cn = self.is_chinese_char(char)
                    if is_cn and subtitle.font_family_cn:
                        font = self.get_font(subtitle.font_family_cn, subtitle.font_size, is_chinese=True)
                    else:
                        font = self.get_font(subtitle.font_family, subtitle.font_size, is_chinese=False)

                    # 尝试使用 TextBlob 以获得更好的亚像素支持，fallback 到 drawString
                    try:
                        blob = skia.TextBlob(char, font)
                        canvas.drawTextBlob(blob, x_offset, y_offset, paint)
                    except (AttributeError, TypeError):
                        # 如果 TextBlob 不可用，使用 drawString
                        canvas.drawString(char, x_offset, y_offset, font, paint)

                    char_width = font.measureText(char)
                    x_offset += char_width + subtitle.letter_spacing
            else:
                x_offset = float(subtitle.x)
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
                            # 尝试使用 TextBlob 以获得更好的亚像素支持
                            try:
                                blob = skia.TextBlob(current_segment, font)
                                canvas.drawTextBlob(blob, x_offset, y_offset, paint)
                            except (AttributeError, TypeError):
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
                    # 尝试使用 TextBlob 以获得更好的亚像素支持
                    try:
                        blob = skia.TextBlob(current_segment, font)
                        canvas.drawTextBlob(blob, x_offset, y_offset, paint)
                    except (AttributeError, TypeError):
                        canvas.drawString(current_segment, x_offset, y_offset, font, paint)

            # 保持浮点精度，不要取整
            y_offset += line_height

