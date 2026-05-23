interface Props {
  activeTab: string;
  onTabChange: (id: string) => void;
  navItems: Array<{ id: string; label: string; icon?: string }>;
}

export default function Sidebar({
  activeTab,
  onTabChange,
  navItems,
}: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-rail" aria-label="主导航">
        {navItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`rail-button ${item.id === activeTab ? "active" : ""}`}
            onClick={() => onTabChange(item.id)}
            aria-label={item.label}
            title={item.label}
          >
            <span className="rail-icon font-mono">{item.icon ?? "□"}</span>
            <span className="rail-label">{item.label}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}
