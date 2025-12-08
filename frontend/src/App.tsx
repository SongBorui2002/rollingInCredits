import React, { useState } from 'react';
import SubtitleEditor from './components/SubtitleEditor';
import { RenderConfig, SubtitleItem } from './types';
import { renderDPX, renderTIFF } from './api';
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

  const handleRender = async (format: 'dpx' | 'tiff') => {
    try {
      const blob = format === 'dpx' 
        ? await renderDPX(config)
        : await renderTIFF(config);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `output.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      alert(`渲染完成！${format.toUpperCase()} 文件已下载`);
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
        </div>
      </div>
      <SubtitleEditor config={config} onConfigChange={handleConfigChange} />
    </div>
  );
}

export default App;

