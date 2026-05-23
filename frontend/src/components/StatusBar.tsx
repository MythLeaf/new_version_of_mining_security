import { useEffect, useState } from "react";
import type { HealthResponse, ScenarioId } from "../api/types";
import { SCENARIO_NAMES } from "../data/demoData";

interface Props {
  health: HealthResponse | null;
  scenario: ScenarioId;
  onScenarioChange: (scenario: ScenarioId) => void;
}

export default function StatusBar({ health, scenario, onScenarioChange }: Props) {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const online = health?.status === "healthy";
  const statusText = online ? "正常" : "离线";
  const dot = online ? "online" : "offline";
  const version = health?.version ?? "—";
  const time = now.toLocaleTimeString("zh-CN", { hour12: false });
  const scenes = Object.entries(SCENARIO_NAMES) as Array<[ScenarioId, string]>;

  return (
    <div className="system-status-bar">
      <div className="top-brand">
        <div className="brand-mark">御界</div>
        <div>
          <div className="brand-name">Yu Jie</div>
          <div className="brand-subtitle font-mono">SECURITY CENTER</div>
        </div>
      </div>
      <nav className="top-scenario-nav" aria-label="场景模式切换">
        {scenes.map(([id, name]) => (
          <button
            key={id}
            type="button"
            className={`top-scenario-item ${scenario === id ? "active" : ""}`}
            onClick={() => onScenarioChange(id)}
          >
            {name}
          </button>
        ))}
      </nav>
      <div className="top-search" aria-hidden="true">
        <span className="top-search-icon">⌕</span>
        <span>查询系统...</span>
      </div>
      <div className="status-actions">
        <div className={`backend-pill ${online ? "online" : "offline"}`}>
          <span className={`status-dot ${dot}`}></span>
          <span>后端状态: {statusText}</span>
        </div>
        <div className="status-icon-btn font-mono" title="版本">
          v{version}
        </div>
        <div className="status-icon-btn font-mono" title="系统时间">
          {time}
        </div>
        <div className="status-alert" title="预警中心">
          !
        </div>
      </div>
    </div>
  );
}
