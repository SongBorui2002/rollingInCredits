import { useState, useEffect, useRef } from 'react';
import {
  SubtitleItem,
  RenderConfig,
  ScrollPreviewResponse,
  ScrollFullPreviewResponse,
  FrameRate,
  FRAME_RATES,
} from '../types';
import { getPreview, getScrollChunk, getScrollFull } from '../api';
import { useDebounce } from '../hooks/useDebounce';
import './SubtitleEditor.css';

type PreviewQuality = 'fast' | 'high';

interface SubtitleEditorProps {
  config: RenderConfig;
  onConfigChange: (config: RenderConfig) => void;
  onRenderParamsChange?: (params: {
    fps: number;
    scrollMode: 'speed' | 'duration';
    scrollSpeed: number;
    totalDurationSec: number;
  }) => void;
}

const QUALITY_SCALE: Record<PreviewQuality, number> = {
  fast: 0.25,
  high: 1,
};

export default function SubtitleEditor({ config, onConfigChange, onRenderParamsChange }: SubtitleEditorProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isRendering, setIsRendering] = useState(false);
  const [renderTime, setRenderTime] = useState<number | null>(null);
  const [scrollChunk, setScrollChunk] = useState<ScrollPreviewResponse | null>(null);
  const [fullScroll, setFullScroll] = useState<ScrollFullPreviewResponse | null>(null);
  const [isLoadingFull, setIsLoadingFull] = useState(false);
  const [useScrollPreview, setUseScrollPreview] = useState(true);
  const [scrollY, setScrollY] = useState(0);
  const [chunkHeight, setChunkHeight] = useState<number>(config.height);
  const [isPlaying, setIsPlaying] = useState(false);
  const [scrollSpeed, setScrollSpeed] = useState<number>(200); // px/s（自由模式）
  const [scrollMode, setScrollMode] = useState<'speed' | 'duration'>('speed');
  const [totalDurationSec, setTotalDurationSec] = useState<number>(20); // 总时长模式（秒）
  const [fps, setFps] = useState<FrameRate>(24); // 默认 24fps
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [actualFps, setActualFps] = useState<number>(0);
  const lastFrameRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);
  // Fixed timestep 相关
  const accumulatorRef = useRef<number>(0);
  const frameIndexRef = useRef<number>(0);
  const lastTimestampRef = useRef<number | null>(null);
  // FPS 统计
  const fpsSamplesRef = useRef<number[]>([]);
  const lastFpsUpdateRef = useRef<number>(0);
  const [selectedSubtitleId, setSelectedSubtitleId] = useState<string | null>(
    config.subtitles[0]?.id || null
  );
  const interactionCanvasRef = useRef<HTMLCanvasElement>(null);
  const [previewQuality, setPreviewQuality] = useState<PreviewQuality>('fast');
  const previewScale = QUALITY_SCALE[previewQuality];
  const scaledWidth = Math.max(1, Math.round(config.width * previewScale));
  const scaledHeight = Math.max(1, Math.round(config.height * previewScale));
  const debouncedScrollY = useDebounce(scrollY, 120);
  const debouncedConfigForFull = useDebounce(config, 500);

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

  // 请求全分辨率完整长图（一次性），配置变更时刷新
  useEffect(() => {
    const requestFull = async () => {
      setIsLoadingFull(true);
      try {
        const response = await getScrollFull({
          ...debouncedConfigForFull,
          preview: false,
          preview_scale: 1,
        });
        setFullScroll(response);
        // 重置滚动位置
        setScrollY(0);
      } catch (error) {
        console.error('Scroll full request failed:', error);
      } finally {
        setIsLoadingFull(false);
      }
    };
    requestFull();
  }, [debouncedConfigForFull]);

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

  // 将滚动参数回传给父级，用于后端渲染请求
  useEffect(() => {
    onRenderParamsChange?.({
      fps,
      scrollMode,
      scrollSpeed,
      totalDurationSec,
    });
  }, [fps, scrollMode, scrollSpeed, totalDurationSec, onRenderParamsChange]);

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

  const displayUrl =
    useScrollPreview && fullScroll ? fullScroll.preview_url
    : useScrollPreview && scrollChunk ? scrollChunk.preview_url
    : previewUrl;
  const displayRenderTime =
    useScrollPreview && fullScroll
      ? fullScroll.render_time_ms
      : useScrollPreview && scrollChunk
        ? scrollChunk.render_time_ms
        : renderTime;
  const totalScrollableHeight =
    useScrollPreview && fullScroll
      ? fullScroll.total_height
      : scrollChunk?.total_height ?? config.height;
  const viewportLogicalHeight = config.height;
  const scrollPixelsTotal = Math.max(0, totalScrollableHeight - viewportLogicalHeight);
  const derivedSpeed = scrollMode === 'duration'
    ? (totalDurationSec > 0 ? scrollPixelsTotal / totalDurationSec : 0)
    : scrollSpeed;
  const pixelsPerFrame = derivedSpeed / fps || 0;

  // 播放控制：基于 fixed timestep 的帧驱动滚动
  useEffect(() => {
    if (!isPlaying) {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      lastTimestampRef.current = null;
      accumulatorRef.current = 0;
      return;
    }

    // 计算每帧的时间（毫秒）
    const frameDuration = 1000 / fps; // ms per frame

    const tick = (ts: number) => {
      if (lastTimestampRef.current == null) {
        lastTimestampRef.current = ts;
        rafRef.current = requestAnimationFrame(tick);
        return;
      }

      const delta = ts - lastTimestampRef.current; // 实际经过的毫秒数
      lastTimestampRef.current = ts;
      accumulatorRef.current += delta;

      // Fixed timestep: 只有当累积时间达到一帧时长时才推进
      let framesToAdvance = 0;
      while (accumulatorRef.current >= frameDuration) {
        accumulatorRef.current -= frameDuration;
        framesToAdvance++;
      }

      // 如果有帧需要推进，更新逻辑状态
      if (framesToAdvance > 0) {
        frameIndexRef.current += framesToAdvance;
        setCurrentFrameIndex(frameIndexRef.current);

        // 根据帧索引计算滚动位置
        // 每帧移动的距离 = scrollSpeed (px/s) / fps (frames/s) = scrollSpeed / fps (px/frame)
        const pixelsPerFrame = derivedSpeed / fps;
        const totalHeight = totalScrollableHeight;
        const maxY = Math.max(0, totalHeight - viewportLogicalHeight);
        const newY = Math.min(maxY, frameIndexRef.current * pixelsPerFrame);
        setScrollY(newY);
      }

      // FPS 统计（每 500ms 更新一次）
      if (ts - lastFpsUpdateRef.current >= 500) {
        fpsSamplesRef.current.push(ts);
        // 只保留最近 1 秒的样本
        const oneSecondAgo = ts - 1000;
        fpsSamplesRef.current = fpsSamplesRef.current.filter(t => t > oneSecondAgo);
        
        if (fpsSamplesRef.current.length >= 2) {
          const timeSpan = fpsSamplesRef.current[fpsSamplesRef.current.length - 1] - fpsSamplesRef.current[0];
          const calculatedFps = ((fpsSamplesRef.current.length - 1) / timeSpan) * 1000;
          setActualFps(calculatedFps);
        }
        lastFpsUpdateRef.current = ts;
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      lastTimestampRef.current = null;
      accumulatorRef.current = 0;
    };
  }, [isPlaying, scrollSpeed, fps, totalScrollableHeight, viewportLogicalHeight]);

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
            {/* 后端渲染的预览图像 / 长图滚动 */}
            {displayUrl ? (
              <div className="scroll-full-wrapper">
                <img
                  src={displayUrl}
                  alt="Preview"
                  className="preview-image"
                  style={{
                    position: 'absolute',
                    top: `-${Math.max(0, scrollY)}px`,
                    left: 0,
                    width: '100%',
                    height: 'auto',
                  }}
                />
              </div>
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
            {displayRenderTime !== null && !isRendering && (
              <div className="render-time">
                渲染时间: {displayRenderTime.toFixed(2)}ms
              </div>
            )}

            {/* 帧率信息显示 */}
            {isPlaying && (
              <div className="fps-indicator">
                <div>目标 FPS: {fps}</div>
                <div>实际 FPS: {actualFps > 0 ? actualFps.toFixed(2) : '--'}</div>
                <div>帧索引: {currentFrameIndex}</div>
                <div>模式: {scrollMode === 'speed' ? '速度' : '总时长'}</div>
                <div>速度: {derivedSpeed.toFixed(2)} px/s</div>
                <div>每帧: {pixelsPerFrame.toFixed(2)} px/frame</div>
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

          <div className="scroll-preview">
            <h3>滚动预览（全分辨率分块）</h3>
            <label className="radio-option">
              <input
                type="checkbox"
                checked={useScrollPreview}
                onChange={(e) => setUseScrollPreview(e.target.checked)}
              />
              <span>使用滚动预览（长图优先，其次分块）</span>
            </label>
            <div className="property-group">
              <label>当前长图高度 (px)</label>
              <input
                type="text"
                value={
                  fullScroll?.total_height ??
                  scrollChunk?.total_height ??
                  '未知'
                }
                readOnly
              />
            </div>
            <div className="property-group">
              <label>帧率 (FPS)</label>
              <select
                value={fps}
                onChange={(e) => {
                  const newFps = parseFloat(e.target.value) as FrameRate;
                  setFps(newFps);
                  // 重置帧索引，保持当前时间位置
                  const currentTime = frameIndexRef.current / fps; // 当前时间（秒）
                  frameIndexRef.current = Math.floor(currentTime * newFps);
                }}
              >
                {FRAME_RATES.map(rate => (
                  <option key={rate} value={rate}>
                    {rate} fps
                  </option>
                ))}
              </select>
            </div>
            <div className="property-group">
              <label>滚动模式</label>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <label className="radio-option">
                  <input
                    type="radio"
                    name="scrollMode"
                    value="speed"
                    checked={scrollMode === 'speed'}
                    onChange={() => setScrollMode('speed')}
                  />
                  <span>按速度 (px/s)</span>
                </label>
                <label className="radio-option">
                  <input
                    type="radio"
                    name="scrollMode"
                    value="duration"
                    checked={scrollMode === 'duration'}
                    onChange={() => setScrollMode('duration')}
                  />
                  <span>按总时长 (秒)</span>
                </label>
              </div>
            </div>

            {scrollMode === 'speed' ? (
              <div className="property-group">
                <label>滚动速度 (px/s)</label>
                <input
                  type="number"
                  min={10}
                  max={2000}
                  value={scrollSpeed}
                  onChange={(e) => setScrollSpeed(Math.max(1, Number(e.target.value)))}
                />
                <small style={{ color: '#888', fontSize: '11px', display: 'block', marginTop: '4px' }}>
                  每帧移动: {pixelsPerFrame.toFixed(2)} px/frame
                </small>
              </div>
            ) : (
              <div className="property-group">
                <label>总时长 (秒)</label>
                <input
                  type="number"
                  min={1}
                  max={600}
                  value={totalDurationSec}
                  onChange={(e) => setTotalDurationSec(Math.max(1, Number(e.target.value)))}
                />
                <small style={{ color: '#888', fontSize: '11px', display: 'block', marginTop: '4px' }}>
                  推导速度: {derivedSpeed.toFixed(2)} px/s · 每帧 {pixelsPerFrame.toFixed(2)} px/frame
                </small>
              </div>
            )}
            <div className="property-group">
              <label>当前位置 y (px)</label>
              <input
                type="number"
                min={0}
                value={Math.floor(scrollY)}
                onChange={(e) => {
                  const next = Math.max(0, Number(e.target.value));
                  setScrollY(next);
                  // 同步更新帧索引
                  frameIndexRef.current = pixelsPerFrame > 0 ? Math.floor(next / pixelsPerFrame) : 0;
                  setCurrentFrameIndex(frameIndexRef.current);
                }}
              />
            </div>
            <div className="property-group">
              <label>当前帧索引</label>
              <input
                type="number"
                min={0}
                value={currentFrameIndex}
                onChange={(e) => {
                  const next = Math.max(0, Math.floor(Number(e.target.value)));
                  frameIndexRef.current = next;
                  setCurrentFrameIndex(next);
                  setScrollY(next * pixelsPerFrame);
                }}
              />
            </div>
            <div className="scroll-preview-actions">
              <button onClick={() => {
                setIsPlaying((v) => !v);
                if (!isPlaying) {
                  // 播放时重置 FPS 统计
                  fpsSamplesRef.current = [];
                  lastFpsUpdateRef.current = performance.now();
                }
              }}>
                {isPlaying ? '暂停' : '播放'}
              </button>
              <button onClick={() => {
                setScrollY(0);
                frameIndexRef.current = 0;
                setCurrentFrameIndex(0);
              }}>回到顶部</button>
            </div>
            {isLoadingFull && <div className="scroll-meta">长图生成中...</div>}
            {fullScroll && (
              <div className="scroll-meta">
                <div>长图高度: {fullScroll.total_height}px</div>
                <div>渲染时间: {fullScroll.render_time_ms.toFixed(2)}ms</div>
              </div>
            )}
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

