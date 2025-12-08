import { RenderConfig, PreviewResponse } from './types';

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

