import { useEffect, useState } from "react";
import type { HealthResponse } from "../api/types";

interface Props {
  health: HealthResponse | null;
  scenarioName: string;
  backendOnline: boolean;
  demoMode?: boolean;
  onMenuToggle?: () => void;
  menuExpanded?: boolean;
}

export default function StatusBar({
  health,
  scenarioName,
  backendOnline,
  demoMode,
  onMenuToggle,
  menuExpanded,
}: Props) {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const statusText = backendOnline ? "在线" : "离线";
  const dot = backendOnline ? "online" : "offline";
  const version = health?.version ?? "—";
  const time = now.toLocaleTimeString("zh-CN", { hour12: false });

  return (
    <>
      <div className="system-status-bar">
        <div className="status-bar-left">
          {onMenuToggle && (
            <button
              type="button"
              className="sidebar-menu-btn"
              aria-label="打开或关闭侧边栏"
              aria-expanded={menuExpanded ?? false}
              onClick={onMenuToggle}
            >
              菜单
            </button>
          )}
          <div className="status-bar-item">
            <span className={`status-dot ${dot}`} aria-hidden="true" />
            <span className="font-mono">系统 {statusText}</span>
          </div>
          <div className="status-bar-item font-mono">v{version}</div>
          <div className="status-bar-item">场景: {scenarioName}</div>
        </div>
        <div className="status-bar-item font-mono" aria-live="polite">
          {time}
        </div>
      </div>
      {!backendOnline && (
        <div className="mock-banner" role="status">
          后端未连接，部分页面将使用本地演示数据。请启动 FastAPI 服务（默认端口 8000）。
        </div>
      )}
      {demoMode && (
        <div className="demo-banner" role="status">
          演示模式：主 Tab 每 12 秒自动轮播，便于路演展示。
        </div>
      )}
    </>
  );
}
