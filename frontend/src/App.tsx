import { useState } from 'react';
import SubtitleEditor from './components/SubtitleEditor';
import { RenderConfig } from './types';
import { renderDPX, renderTIFF, renderTiffSequenceFps } from './api';
import './App.css';

function App() {
  const [config, setConfig] = useState<RenderConfig>({
    width: 1920,
    height: 1080,
    subtitles: [
      {
        id: '1',
        text: '导演\nDirector',
        x: 960,
        y: 400,
        font_family: 'Arial',
        font_family_cn: '/System/Library/Fonts/STHeiti Light.ttc',
        font_size: 48,
        letter_spacing: 0,
        line_height: 1.5,
        color: [255, 255, 255],
      },
      {
        id: '2',
        text: '制片人\nProducer',
        x: 960,
        y: 500,
        font_family: 'Arial',
        font_family_cn: '/System/Library/Fonts/STHeiti Light.ttc',
        font_size: 48,
        letter_spacing: 0,
        line_height: 1.5,
        color: [255, 255, 255],
      },
    ],
    background_color: [0, 0, 0],
    preview: false,
  });

  const handleConfigChange = (newConfig: RenderConfig) => {
    setConfig(newConfig);
  };

  const [renderParams, setRenderParams] = useState({
    fps: 24,
    scrollMode: 'speed' as 'speed' | 'duration',
    scrollSpeed: 200,
    totalDurationSec: 20,
    ensureNoScroll: false,
    optimizationMode: null as 'duration' | 'layout' | null,
  });

  const handleRender = async (format: 'dpx' | 'tiff' | 'tiff-seq-fps') => {
    try {
      const blob = format === 'dpx'
        ? await renderDPX(config)
        : format === 'tiff'
          ? await renderTIFF(config)
          : await renderTiffSequenceFps({
              config,
              fps: renderParams.fps,
              duration_sec: renderParams.scrollMode === 'duration' ? renderParams.totalDurationSec : null,
              scroll_speed: renderParams.scrollMode === 'speed' ? renderParams.scrollSpeed : null,
              ensure_no_scroll: renderParams.ensureNoScroll || undefined,
              optimization_mode: renderParams.optimizationMode || undefined,
            });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = format === 'tiff-seq-fps' ? 'zip' : format;
      a.download = `output.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      const friendly = format === 'tiff-seq-fps' ? 'TIFF 序列 (FPS) (ZIP)' : format.toUpperCase();
      alert(`渲染完成！${friendly} 文件已下载`);
    } catch (error) {
      console.error('Render failed:', error);
      alert('渲染失败: ' + (error as Error).message);
    }
  };

  return (
    <div className="app">
      <div className="app-header">
        <h1>RollingInCredits - 字幕编辑器</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={() => handleRender('dpx')} className="render-button">
            渲染 DPX
          </button>
          <button onClick={() => handleRender('tiff')} className="render-button">
            渲染 TIFF
          </button>
          <button onClick={() => handleRender('tiff-seq-fps')} className="render-button">
            渲染 TIFF 序列（按 FPS）
          </button>
        </div>
      </div>
      <SubtitleEditor
        config={config}
        onConfigChange={handleConfigChange}
        onRenderParamsChange={setRenderParams}
      />
    </div>
  );
}

export default App;

