export interface SubtitleItem {
  id: string;
  text: string;
  x: number;
  y: number;
  font_family: string;  // 英文字体
  font_family_cn?: string | null;  // 中文字体（可选）
  font_size: number;
  letter_spacing: number;
  line_height: number;
  color: [number, number, number];
}

export interface RenderConfig {
  width: number;
  height: number;
  subtitles: SubtitleItem[];
  background_color: [number, number, number];
  preview: boolean;
  preview_scale?: number;
}

export interface PreviewResponse {
  preview_url: string;
  render_time_ms: number;
}

export interface ScrollPreviewRequest {
  config: RenderConfig;
  y_start: number;
  chunk_height: number;
}

export interface ScrollPreviewResponse {
  preview_url: string;
  render_time_ms: number;
  total_height: number;
  y_start: number;
  chunk_height: number;
}

export interface ScrollFullPreviewResponse {
  preview_url: string;
  render_time_ms: number;
  total_height: number;
}

// 电影级帧率选项
export type FrameRate = 23.976 | 24 | 25 | 29.97 | 30 | 60 | 120;

export const FRAME_RATES: FrameRate[] = [23.976, 24, 25, 29.97, 30, 60, 120];

// 逐帧渲染序列请求
export interface RenderSequenceRequest {
  config: RenderConfig;
  fps: number; // 目标帧率
  duration_sec?: number | null; // 总时长（秒），与 scroll_speed 二选一，优先 duration
  scroll_speed?: number | null; // 滚动速度（px/s），当未提供 duration 时使用
}

