import { Lightning, UploadSimple } from "@phosphor-icons/react";

type AppHeaderProps = {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onImport: (event: React.ChangeEvent<HTMLInputElement>) => void;
};

export function AppHeader({ fileInputRef, onImport }: AppHeaderProps) {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark">
          <Lightning weight="fill" />
        </span>
        <span>
          NRG<span className="brand-accent">_Grid</span>
        </span>
      </div>
      <div className="status-pill">
        <span className="status-dot" /> Preview engine ready
      </div>
      <button
        className="icon-button"
        title="Import scenario"
        onClick={() => fileInputRef.current?.click()}
      >
        <UploadSimple size={19} />
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json"
        hidden
        onChange={onImport}
      />
    </header>
  );
}
