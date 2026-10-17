import "./Tabs.css";

export interface TabItem {
  key: string;
  label: string;
  count?: number;
}

export function Tabs({ items, active, onChange }: { items: TabItem[]; active: string; onChange: (key: string) => void }) {
  return (
    <div className="tabs" role="tablist">
      {items.map((item) => (
        <button
          key={item.key}
          role="tab"
          aria-selected={active === item.key}
          className={active === item.key ? "tab tab-active" : "tab"}
          onClick={() => onChange(item.key)}
        >
          {item.label}
          {typeof item.count === "number" && <span className="tab-count">{item.count}</span>}
        </button>
      ))}
    </div>
  );
}
