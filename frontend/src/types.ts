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

