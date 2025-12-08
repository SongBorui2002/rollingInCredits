import { useState, useEffect, useRef } from 'react';
import { SubtitleItem, RenderConfig } from '../types';
import { getPreview } from '../api';
import { useDebounce } from '../hooks/useDebounce';
import './SubtitleEditor.css';

type PreviewQuality = 'fast' | 'high';

interface SubtitleEditorProps {
  config: RenderConfig;
  onConfigChange: (config: RenderConfig) => void;
}

const QUALITY_SCALE: Record<PreviewQuality, number> = {
  fast: 0.25,
  high: 1,
};

export default function SubtitleEditor({ config, onConfigChange }: SubtitleEditorProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isRendering, setIsRendering] = useState(false);
  const [renderTime, setRenderTime] = useState<number | null>(null);
  const [selectedSubtitleId, setSelectedSubtitleId] = useState<string | null>(
    config.subtitles[0]?.id || null
  );
  const interactionCanvasRef = useRef<HTMLCanvasElement>(null);
  const [previewQuality, setPreviewQuality] = useState<PreviewQuality>('fast');
  const previewScale = QUALITY_SCALE[previewQuality];
  const scaledWidth = Math.max(1, Math.round(config.width * previewScale));
  const scaledHeight = Math.max(1, Math.round(config.height * previewScale));

  // 防抖配置
  const debouncedConfig = useDebounce(config, 300);

  // 请求预览
  useEffect(() => {
    const requestPreview = async () => {
      setIsRendering(true);
      try {
        const response = await getPreview({
          ...debouncedConfig,
          preview: true,
          preview_scale: previewScale,
        });
        setPreviewUrl(response.preview_url);
        setRenderTime(response.render_time_ms);
      } catch (error) {
        console.error('Preview request failed:', error);
      } finally {
        setIsRendering(false);
      }
    };

    requestPreview();
  }, [debouncedConfig, previewScale]);

  // 绘制交互层
  useEffect(() => {
    const canvas = interactionCanvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 设置画布大小
    canvas.width = scaledWidth;
    canvas.height = scaledHeight;

    // 清空画布
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 绘制选择框和拖拽手柄
    if (selectedSubtitleId) {
      const subtitle = config.subtitles.find(s => s.id === selectedSubtitleId);
      if (subtitle) {
        // 估算文本尺寸（用于显示选择框）
        const estimatedWidth = subtitle.text.length * subtitle.font_size * 0.6;
        const estimatedHeight = subtitle.text.split('\n').length * subtitle.font_size * subtitle.line_height;

        // 绘制选择框
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        const scaledX = subtitle.x * previewScale;
        const scaledY = subtitle.y * previewScale;
        const scaledFontSize = subtitle.font_size * previewScale;
        const scaledWidthEstimate = estimatedWidth * previewScale;
        const scaledHeightEstimate = estimatedHeight * previewScale;

        ctx.strokeRect(
          scaledX - 5,
          scaledY - scaledFontSize,
          scaledWidthEstimate + 10,
          scaledHeightEstimate + 10
        );
        ctx.setLineDash([]);

        // 绘制位置指示器
        ctx.fillStyle = '#00ff00';
        ctx.beginPath();
        ctx.arc(scaledX, scaledY, 4, 0, Math.PI * 2);
        ctx.fill();
      }
    }
   }, [config, selectedSubtitleId, previewScale]);

  const handleSubtitleChange = (id: string, updates: Partial<SubtitleItem>) => {
    const newSubtitles = config.subtitles.map(s =>
      s.id === id ? { ...s, ...updates } : s
    );
    onConfigChange({ ...config, subtitles: newSubtitles });
  };

  const handleCanvasSizeChange = (dimension: 'width' | 'height', value: number) => {
    if (!Number.isFinite(value)) {
      return;
    }
    const min = dimension === 'width' ? 0 : 0;
    const max = dimension === 'width' ? 7680 : 4320;
    const clamped = Math.max(min, Math.min(max, Math.round(value)));
    if (clamped === config[dimension]) {
      return;
    }
    onConfigChange({ ...config, [dimension]: clamped });
  };

  const selectedSubtitle = config.subtitles.find(s => s.id === selectedSubtitleId);

  return (
    <div className="subtitle-editor">
      <div className="editor-main">
        {/* 预览区域 */}
        <div className="preview-container">
          <div
            className="preview-wrapper"
            style={{
              width: '100%',
              height: 'auto',
              maxWidth: '100%',
              maxHeight: 'auto',
              aspectRatio: `${config.width} / ${config.height}`,
            }}
          >
            {/* 后端渲染的预览图像 */}
            {previewUrl ? (
              <img
                src={previewUrl}
                alt="Preview"
                className="preview-image"
                style={{ width: '100%', height: '100%' }}
              />
            ) : (
              <div className="preview-placeholder">
                <span>等待预览...</span>
              </div>
            )}

            {/* 交互层 Canvas */}
            <canvas
              ref={interactionCanvasRef}
              className="interaction-layer"
              style={{ width: '100%', height: '100%' }}
            />

            {/* 渲染状态指示器 */}
            {isRendering && (
              <div className="render-indicator">
                <div className="spinner"></div>
                <span>渲染中...</span>
              </div>
            )}

            {/* 渲染时间显示 */}
            {renderTime !== null && !isRendering && (
              <div className="render-time">
                渲染时间: {renderTime.toFixed(2)}ms
              </div>
            )}
          </div>
        </div>

        {/* 控制面板 */}
        <div className="control-panel">
          <h2>字幕编辑器</h2>

          <div className="canvas-settings">
            <h3>渲染分辨率</h3>
            <div className="property-group">
              <label>宽度 (px)</label>
              <input
                type="number"
                min={0}
                max={7680}
                value={config.width}
                onChange={(e) => handleCanvasSizeChange('width', Number(e.target.value))}
              />
            </div>
            <div className="property-group">
              <label>高度 (px)</label>
              <input
                type="number"
                min={320}
                max={4320}
                value={config.height}
                onChange={(e) => handleCanvasSizeChange('height', Number(e.target.value))}
              />
            </div>
            <small style={{ color: '#999', fontSize: '12px' }}>
              实时预览使用快速/高清模式；最终渲染使用此分辨率输出。
            </small>
          </div>

          <div className="preview-quality">
            <h3>预览质量</h3>
            <label className="radio-option">
              <input
                type="radio"
                name="previewQuality"
                value="fast"
                checked={previewQuality === 'fast'}
                onChange={() => setPreviewQuality('fast')}
              />
              <span>快速预览（降分辨率）</span>
            </label>
            <label className="radio-option">
              <input
                type="radio"
                name="previewQuality"
                value="high"
                checked={previewQuality === 'high'}
                onChange={() => setPreviewQuality('high')}
              />
              <span>高质量预览（全分辨率）</span>
            </label>
          </div>

          {/* 字幕列表 */}
          <div className="subtitle-list">
            <h3>字幕列表</h3>
            {config.subtitles.map(subtitle => (
              <div
                key={subtitle.id}
                className={`subtitle-item ${selectedSubtitleId === subtitle.id ? 'selected' : ''}`}
                onClick={() => setSelectedSubtitleId(subtitle.id)}
              >
                {subtitle.text.substring(0, 30)}...
              </div>
            ))}
          </div>

          {/* 字幕属性编辑 */}
          {selectedSubtitle && (
            <div className="subtitle-properties">
              <h3>字幕属性</h3>

              <div className="property-group">
                <label>文本内容</label>
                <textarea
                  value={selectedSubtitle.text}
                  onChange={(e) => handleSubtitleChange(selectedSubtitle.id, { text: e.target.value })}
                  rows={3}
                />
              </div>

              <div className="property-group">
                <label>X 位置</label>
                <input
                  type="number"
                  value={selectedSubtitle.x}
                  onChange={(e) => handleSubtitleChange(selectedSubtitle.id, { x: parseInt(e.target.value) || 0 })}
                />
              </div>

              <div className="property-group">
                <label>Y 位置</label>
                <input
                  type="number"
                  value={selectedSubtitle.y}
                  onChange={(e) => handleSubtitleChange(selectedSubtitle.id, { y: parseInt(e.target.value) || 0 })}
                />
              </div>

              <div className="property-group">
                <label>英文字体</label>
                <input
                  type="text"
                  value={selectedSubtitle.font_family}
                  onChange={(e) => handleSubtitleChange(selectedSubtitle.id, { font_family: e.target.value })}
                  placeholder="例如: Arial, Times New Roman"
                />
              </div>

              <div className="property-group">
                <label>中文字体（可选）</label>
                <input
                  type="text"
                  value={selectedSubtitle.font_family_cn || ''}
                  onChange={(e) => handleSubtitleChange(selectedSubtitle.id, { 
                    font_family_cn: e.target.value || null 
                  })}
                  placeholder="例如: /System/Library/Fonts/STHeiti Light.ttc"
                />
                <small style={{ color: '#888', fontSize: '12px', display: 'block', marginTop: '4px' }}>
                  留空则使用系统默认中文字体。macOS常见路径: /System/Library/Fonts/STHeiti Light.ttc
                </small>
              </div>

              <div className="property-group">
                <label>字号</label>
                <input
                  type="number"
                  value={selectedSubtitle.font_size}
                  onChange={(e) => handleSubtitleChange(selectedSubtitle.id, { font_size: parseInt(e.target.value) || 12 })}
                  min="12"
                  max="200"
                />
              </div>

              <div className="property-group">
                <label>字间距 (像素)</label>
                <input
                  type="number"
                  value={selectedSubtitle.letter_spacing}
                  onChange={(e) => handleSubtitleChange(selectedSubtitle.id, { letter_spacing: parseFloat(e.target.value) || 0 })}
                  step="0.5"
                  min="-10"
                  max="20"
                />
              </div>

              <div className="property-group">
                <label>行间距 (倍数)</label>
                <input
                  type="number"
                  value={selectedSubtitle.line_height}
                  onChange={(e) => handleSubtitleChange(selectedSubtitle.id, { line_height: parseFloat(e.target.value) || 1.0 })}
                  step="0.1"
                  min="0.5"
                  max="3.0"
                />
              </div>

              <div className="property-group">
                <label>颜色 (RGB)</label>
                <div className="color-inputs">
                  <input
                    type="number"
                    value={selectedSubtitle.color[0]}
                    onChange={(e) => {
                      const newColor: [number, number, number] = [
                        parseInt(e.target.value) || 0,
                        selectedSubtitle.color[1],
                        selectedSubtitle.color[2],
                      ];
                      handleSubtitleChange(selectedSubtitle.id, { color: newColor });
                    }}
                    min="0"
                    max="255"
                    placeholder="R"
                  />
                  <input
                    type="number"
                    value={selectedSubtitle.color[1]}
                    onChange={(e) => {
                      const newColor: [number, number, number] = [
                        selectedSubtitle.color[0],
                        parseInt(e.target.value) || 0,
                        selectedSubtitle.color[2],
                      ];
                      handleSubtitleChange(selectedSubtitle.id, { color: newColor });
                    }}
                    min="0"
                    max="255"
                    placeholder="G"
                  />
                  <input
                    type="number"
                    value={selectedSubtitle.color[2]}
                    onChange={(e) => {
                      const newColor: [number, number, number] = [
                        selectedSubtitle.color[0],
                        selectedSubtitle.color[1],
                        parseInt(e.target.value) || 0,
                      ];
                      handleSubtitleChange(selectedSubtitle.id, { color: newColor });
                    }}
                    min="0"
                    max="255"
                    placeholder="B"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

