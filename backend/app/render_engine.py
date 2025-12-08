"""
渲染引擎 - 使用 Pillow 进行文本渲染，OIIO 进行专业格式输出
策略：
1. 文本渲染使用 Pillow（因为 OIIO 不直接支持文本渲染）
2. 预览输出：Pillow -> PNG
3. 最终输出：Pillow -> OIIO -> DPX
这样可以保证预览和最终渲染使用相同的文本渲染逻辑，确保一致性
"""
import time
import platform
import tempfile
import os
from io import BytesIO
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import OpenImageIO as oiio

from app.models import SubtitleItem, RenderConfig


class RenderEngine:
    """统一的渲染引擎"""
    
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
                    ImageFont.truetype(path, 12)
                    self.default_cn_font = path
                    break
                except:
                    continue
            # 如果找不到 PingFang，尝试其他中文字体
            if not self.default_cn_font:
                try:
                    # 尝试使用系统默认字体（通常支持中文）
                    self.default_cn_font = "/System/Library/Fonts/STHeiti Light.ttc"
                    ImageFont.truetype(self.default_cn_font, 12)
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
                    ImageFont.truetype(path, 12)
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
    
    def get_font(self, font_family: str, font_size: int, is_chinese: bool = False):
        """获取字体（带缓存）"""
        cache_key = f"{font_family}_{font_size}_{is_chinese}"
        if cache_key not in self.font_cache:
            try:
                # 尝试加载指定字体
                font = ImageFont.truetype(font_family, font_size)
            except:
                # 如果失败，使用默认字体
                if is_chinese:
                    if self.default_cn_font:
                        try:
                            font = ImageFont.truetype(self.default_cn_font, font_size)
                        except:
                            font = ImageFont.load_default()
                    else:
                        font = ImageFont.load_default()
                else:
                    if self.default_en_font:
                        try:
                            font = ImageFont.truetype(self.default_en_font, font_size)
                        except:
                            font = ImageFont.load_default()
                    else:
                        font = ImageFont.load_default()
            self.font_cache[cache_key] = font
        return self.font_cache[cache_key]
    
    def is_chinese_char(self, char: str) -> bool:
        """判断字符是否为中文"""
        return '\u4e00' <= char <= '\u9fff'
    
    def render_preview(self, config: RenderConfig) -> Tuple[bytes, float]:
        """
        渲染预览帧（PNG格式，用于前端显示）
        使用与最终渲染相同的逻辑，只是输出格式不同
        """
        start_time = time.time()
        
        # 创建图像
        img = Image.new('RGB', (config.width, config.height), config.background_color)
        draw = ImageDraw.Draw(img)
        
        # 渲染每个字幕
        for subtitle in config.subtitles:
            self._render_subtitle(draw, subtitle, config.width, config.height)
        
        # 转换为 PNG
        output = BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        
        render_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        return output.read(), render_time
    
    def render_final_dpx(self, config: RenderConfig) -> Tuple[bytes, float]:
        """
        渲染最终输出（DPX格式）
        使用与预览完全相同的文本渲染逻辑，然后通过 OIIO 输出为 DPX
        """
        start_time = time.time()
        
        # 创建图像（使用与预览相同的逻辑）
        img = Image.new('RGB', (config.width, config.height), config.background_color)
        draw = ImageDraw.Draw(img)
        
        # 渲染每个字幕（使用相同的函数，确保一致性）
        for subtitle in config.subtitles:
            self._render_subtitle(draw, subtitle, config.width, config.height)
        
        # 转换为 numpy 数组
        img_array = np.array(img, dtype=np.uint8)
        
        # 使用 OIIO 保存为 DPX 格式
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.dpx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 创建 OIIO ImageSpec（DPX 通常使用 10-bit）
            spec = oiio.ImageSpec(config.width, config.height, 3, oiio.UINT8)
            spec.attribute("oiio:BitsPerSample", 8)  # DPX 支持 8, 10, 12, 16 bit
            
            # 创建 ImageBuf
            buf = oiio.ImageBuf(spec)
            
            # 设置像素数据（OIIO 使用 (height, width, channels) 格式）
            # 注意：需要转换维度顺序
            img_reshaped = img_array.reshape((config.height, config.width, 3))
            buf.set_pixels(oiio.ROI(0, config.width, 0, config.height, 0, 1, 0, 3), img_reshaped)
            
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
        
        # 创建图像（使用与预览相同的逻辑）
        img = Image.new('RGB', (config.width, config.height), config.background_color)
        draw = ImageDraw.Draw(img)
        
        # 渲染每个字幕（使用相同的函数，确保一致性）
        for subtitle in config.subtitles:
            self._render_subtitle(draw, subtitle, config.width, config.height)
        
        # 转换为 numpy 数组
        img_array = np.array(img, dtype=np.uint8)
        
        # 使用 OIIO 保存为 TIFF 格式
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 创建 OIIO ImageSpec
            spec = oiio.ImageSpec(config.width, config.height, 3, oiio.UINT8)
            
            # 创建 ImageBuf
            buf = oiio.ImageBuf(spec)
            
            # 设置像素数据
            img_reshaped = img_array.reshape((config.height, config.width, 3))
            buf.set_pixels(oiio.ROI(0, config.width, 0, config.height, 0, 1, 0, 3), img_reshaped)
            
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
    
    def _render_subtitle(self, draw: ImageDraw.Draw, subtitle: SubtitleItem, 
                        canvas_width: int, canvas_height: int):
        """
        渲染单个字幕
        这是核心渲染逻辑，预览和最终渲染都使用这个方法
        支持中英文字体分离
        """
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
                    
                    draw.text(
                        (x_offset, y_offset),
                        char,
                        fill=subtitle.color,
                        font=font
                    )
                    # 获取字符宽度并添加字间距
                    char_bbox = draw.textbbox((0, 0), char, font=font)
                    char_width = char_bbox[2] - char_bbox[0]
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
                            draw.text(
                                (x_offset, y_offset),
                                current_segment,
                                fill=subtitle.color,
                                font=font
                            )
                            # 计算已渲染文本的宽度
                            bbox = draw.textbbox((0, 0), current_segment, font=font)
                            x_offset += bbox[2] - bbox[0]
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
                    draw.text(
                        (x_offset, y_offset),
                        current_segment,
                        fill=subtitle.color,
                        font=font
                    )
            
            # 移动到下一行
            y_offset += int(subtitle.font_size * subtitle.line_height)

