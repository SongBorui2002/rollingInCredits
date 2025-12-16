import {
  RenderConfig,
  PreviewResponse,
  ScrollPreviewRequest,
  ScrollPreviewResponse,
  ScrollFullPreviewResponse,
  RenderSequenceRequest,
} from './types';

const API_BASE = '/api';

export async function getPreview(config: RenderConfig): Promise<PreviewResponse> {
  const response = await fetch(`${API_BASE}/preview`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    throw new Error(`Preview request failed: ${response.statusText}`);
  }

  return response.json();
}

export async function renderDPX(config: RenderConfig): Promise<Blob> {
  const response = await fetch(`${API_BASE}/render/dpx`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    throw new Error(`Render request failed: ${response.statusText}`);
  }

  return response.blob();
}

export async function renderTIFF(config: RenderConfig): Promise<Blob> {
  const response = await fetch(`${API_BASE}/render/tiff`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    throw new Error(`Render request failed: ${response.statusText}`);
  }

  return response.blob();
}

export async function getScrollChunk(
  payload: ScrollPreviewRequest,
): Promise<ScrollPreviewResponse> {
  const response = await fetch(`${API_BASE}/preview/scroll-chunk`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Scroll chunk request failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getScrollFull(
  config: RenderConfig,
): Promise<ScrollFullPreviewResponse> {
  const response = await fetch(`${API_BASE}/preview/scroll-full`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    throw new Error(`Scroll full request failed: ${response.statusText}`);
  }

  return response.json();
}

// 按 FPS/时长/速度 逐帧渲染 TIFF 序列（ZIP）
export async function renderTiffSequenceFps(req: RenderSequenceRequest): Promise<Blob> {
  const response = await fetch(`${API_BASE}/render/tiff-seq-fps`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    throw new Error(`Render TIFF sequence (fps) request failed: ${response.statusText}`);
  }

  return response.blob();
}

