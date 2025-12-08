"""
渲染引擎 - 使用 Skia 进行文本渲染，OIIO 进行专业格式输出
Skia 版本提供更高质量的文本渲染（更好的抗锯齿、字体度量等）

策略：
1. 文本渲染使用 Skia（高质量渲染）
2. 预览输出：Skia -> PNG
3. 最终输出：Skia -> OIIO -> DPX/TIFF
这样可以保证预览和最终渲染使用相同的文本渲染逻辑，确保一致性
"""
import time
import platform
import tempfile
import os
from io import BytesIO
from typing import List, Tuple, Optional
import numpy as np
import skia
import OpenImageIO as oiio

from app.models import SubtitleItem, RenderConfig


class RenderEngineSkia:
    """使用 Skia 的统一渲染引擎"""
    
    def __init__(self):
        self.font_cache = {}
        self._init_default_fonts()
    
    def _init_default_fonts(self):
        """初始化默认字体路径"""
        system = platform.system()
        if system == "Darwin":  # macOS
            # 尝试多个可能的 PingFang 字体路径
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
                except:
                    continue
            # 如果找不到 PingFang，尝试其他中文字体
            if not self.default_cn_font:
                try:
                    self.default_cn_font = "/System/Library/Fonts/STHeiti Light.ttc"
                    skia.Typeface.MakeFromFile(self.default_cn_font)
                except:
                    self.default_cn_font = None
            
            # 英文字体
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
                except:
                    continue
        elif system == "Windows":
            self.default_cn_font = "C:/Windows/Fonts/msyh.ttc"  # 微软雅黑
            self.default_en_font = "C:/Windows/Fonts/arial.ttf"
        else:  # Linux
            self.default_cn_font = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
            self.default_en_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    def get_font(self, font_family: str, font_size: int, is_chinese: bool = False) -> skia.Font:
        """获取 Skia 字体（带缓存）"""
        cache_key = f"{font_family}_{font_size}_{is_chinese}"
        if cache_key not in self.font_cache:
            try:
                # 尝试加载指定字体
                typeface = skia.Typeface.MakeFromFile(font_family)
            except:
                # 如果失败，使用默认字体
                if is_chinese:
                    if self.default_cn_font:
                        try:
                            typeface = skia.Typeface.MakeFromFile(self.default_cn_font)
                        except:
                            typeface = skia.Typeface.MakeDefault()
                    else:
                        typeface = skia.Typeface.MakeDefault()
                else:
                    if self.default_en_font:
                        try:
                            typeface = skia.Typeface.MakeFromFile(self.default_en_font)
                        except:
                            typeface = skia.Typeface.MakeDefault()
                    else:
                        typeface = skia.Typeface.MakeDefault()
            
            # 创建 Skia Font 对象
            font = skia.Font(typeface, font_size)
            self.font_cache[cache_key] = font
        return self.font_cache[cache_key]
    
    def is_chinese_char(self, char: str) -> bool:
        """判断字符是否为中文"""
        return '\u4e00' <= char <= '\u9fff'
    
    def render_preview(self, config: RenderConfig) -> Tuple[bytes, float]:
        """
        渲染预览帧（PNG格式，用于前端显示）
        使用与最终渲染相同的逻辑，只是输出格式不同
        预览模式下使用 1/4 分辨率以提升实时性
        """
        start_time = time.time()
        
        # 预览模式降采样，提高渲染速度
        preview_scale = config.preview_scale if config.preview else 1.0
        preview_scale = max(0.1, min(1.0, preview_scale))
        surface_width = max(1, int(config.width * preview_scale))
        surface_height = max(1, int(config.height * preview_scale))
        
        # 使用 Skia 渲染
        surface = skia.Surface(surface_width, surface_height)
        canvas = surface.getCanvas()
        
        # 缩放画布，保持逻辑坐标仍为原始分辨率
        if preview_scale != 1.0:
            canvas.scale(preview_scale, preview_scale)
        
        # 设置背景色
        canvas.clear(skia.Color(
            config.background_color[0],
            config.background_color[1],
            config.background_color[2]
        ))
        
        # 渲染每个字幕
        for subtitle in config.subtitles:
            self._render_subtitle(canvas, subtitle, config.width, config.height)
        
        # 转换为 PNG
        image = surface.makeImageSnapshot()
        # encodeToData 需要格式和质量参数，或者无参数（自动检测）
        png_data = image.encodeToData(skia.EncodedImageFormat.kPNG, 100)
        
        render_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        return bytes(png_data), render_time
    
    def render_final_dpx(self, config: RenderConfig) -> Tuple[bytes, float]:
        """
        渲染最终输出（DPX格式）
        使用与预览完全相同的文本渲染逻辑，然后通过 OIIO 输出为 DPX
        """
        start_time = time.time()
        
        # 使用 Skia 渲染（与预览相同的逻辑）
        surface = skia.Surface(config.width, config.height)
        canvas = surface.getCanvas()
        
        # 设置背景色
        canvas.clear(skia.Color(
            config.background_color[0],
            config.background_color[1],
            config.background_color[2]
        ))
        
        # 渲染每个字幕（使用相同的函数，确保一致性）
        for subtitle in config.subtitles:
            self._render_subtitle(canvas, subtitle, config.width, config.height)
        
        # 获取像素数据
        image = surface.makeImageSnapshot()
        pixels = image.tobytes()
        
        # 转换为 numpy 数组
        img_array = np.frombuffer(pixels, dtype=np.uint8)
        img_array = img_array.reshape((config.height, config.width, 4))  # RGBA
        img_array = img_array[:, :, :3]  # 转换为 RGB
        
        # 使用 OIIO 保存为 DPX 格式
        with tempfile.NamedTemporaryFile(suffix='.dpx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 创建 OIIO ImageSpec
            spec = oiio.ImageSpec(config.width, config.height, 3, oiio.UINT8)
            spec.attribute("oiio:BitsPerSample", 8)
            
            # 创建 ImageBuf
            buf = oiio.ImageBuf(spec)
            
            # 设置像素数据
            buf.set_pixels(oiio.ROI(0, config.width, 0, config.height, 0, 1, 0, 3), img_array)
            
            # 写入 DPX 文件
            buf.write(tmp_path)
            
            # 读取文件内容
            with open(tmp_path, 'rb') as f:
                dpx_data = f.read()
            
            render_time = (time.time() - start_time) * 1000
            
            return dpx_data, render_time
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def render_final_tiff(self, config: RenderConfig) -> Tuple[bytes, float]:
        """
        渲染最终输出（TIFF格式）
        使用与预览完全相同的文本渲染逻辑，然后通过 OIIO 输出为 TIFF
        """
        start_time = time.time()
        
        # 使用 Skia 渲染（与预览相同的逻辑）
        surface = skia.Surface(config.width, config.height)
        canvas = surface.getCanvas()
        
        # 设置背景色
        canvas.clear(skia.Color(
            config.background_color[0],
            config.background_color[1],
            config.background_color[2]
        ))
        
        # 渲染每个字幕（使用相同的函数，确保一致性）
        for subtitle in config.subtitles:
            self._render_subtitle(canvas, subtitle, config.width, config.height)
        
        # 获取像素数据
        image = surface.makeImageSnapshot()
        pixels = image.tobytes()
        
        # 转换为 numpy 数组
        img_array = np.frombuffer(pixels, dtype=np.uint8)
        img_array = img_array.reshape((config.height, config.width, 4))  # RGBA
        img_array = img_array[:, :, :3]  # 转换为 RGB
        
        # 使用 OIIO 保存为 TIFF 格式
        with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 创建 OIIO ImageSpec
            spec = oiio.ImageSpec(config.width, config.height, 3, oiio.UINT8)
            
            # 创建 ImageBuf
            buf = oiio.ImageBuf(spec)
            
            # 设置像素数据
            buf.set_pixels(oiio.ROI(0, config.width, 0, config.height, 0, 1, 0, 3), img_array)
            
            # 写入 TIFF 文件
            buf.write(tmp_path)
            
            # 读取文件内容
            with open(tmp_path, 'rb') as f:
                tiff_data = f.read()
            
            render_time = (time.time() - start_time) * 1000
            
            return tiff_data, render_time
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def _render_subtitle(self, canvas: skia.Canvas, subtitle: SubtitleItem, 
                        canvas_width: int, canvas_height: int):
        """
        渲染单个字幕
        这是核心渲染逻辑，预览和最终渲染都使用这个方法
        支持中英文字体分离
        """
        # 创建 Skia Paint 对象
        paint = skia.Paint(
            AntiAlias=True,  # 启用抗锯齿
            Style=skia.Paint.kFill_Style,
        )
        
        # 设置颜色
        paint.setColor(skia.Color(
            subtitle.color[0],
            subtitle.color[1],
            subtitle.color[2]
        ))
        
        # 处理多行文本
        lines = subtitle.text.split('\n')
        y_offset = subtitle.y
        
        for line in lines:
            if not line.strip():
                y_offset += int(subtitle.font_size * subtitle.line_height)
                continue
            
            # 处理字间距
            if subtitle.letter_spacing != 0:
                # 逐字符渲染以实现字间距和中英文字体分离
                x_offset = subtitle.x
                for char in line:
                    # 根据字符类型选择字体
                    is_cn = self.is_chinese_char(char)
                    if is_cn and subtitle.font_family_cn:
                        font = self.get_font(subtitle.font_family_cn, subtitle.font_size, is_chinese=True)
                    else:
                        font = self.get_font(subtitle.font_family, subtitle.font_size, is_chinese=False)
                    
                    # 使用 Skia 绘制文本
                    canvas.drawString(char, x_offset, y_offset, font, paint)
                    
                    # 获取字符宽度并添加字间距
                    char_width = font.measureText(char)  # 返回 float
                    x_offset += char_width + subtitle.letter_spacing
            else:
                # 正常渲染（无字间距，但需要处理中英文字体分离）
                # 将文本按中英文分组
                x_offset = subtitle.x
                current_segment = ""
                current_is_cn = None
                
                for char in line:
                    is_cn = self.is_chinese_char(char)
                    
                    # 如果字符类型改变，先渲染之前的段落
                    if current_is_cn is not None and is_cn != current_is_cn:
                        if current_segment:
                            font = self.get_font(
                                subtitle.font_family_cn if current_is_cn else subtitle.font_family,
                                subtitle.font_size,
                                is_chinese=current_is_cn
                            )
                            canvas.drawString(current_segment, x_offset, y_offset, font, paint)
                            
                            # 计算已渲染文本的宽度
                            segment_width = font.measureText(current_segment)  # 返回 float
                            x_offset += segment_width
                        current_segment = ""
                    
                    current_segment += char
                    current_is_cn = is_cn
                
                # 渲染最后一段
                if current_segment:
                    font = self.get_font(
                        subtitle.font_family_cn if current_is_cn else subtitle.font_family,
                        subtitle.font_size,
                        is_chinese=current_is_cn if current_is_cn is not None else False
                    )
                    canvas.drawString(current_segment, x_offset, y_offset, font, paint)
            
            # 移动到下一行
            y_offset += int(subtitle.font_size * subtitle.line_height)

