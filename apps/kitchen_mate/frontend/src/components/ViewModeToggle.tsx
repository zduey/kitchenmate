interface ViewModeToggleProps {
  mode: "grid" | "tags";
  onChange: (mode: "grid" | "tags") => void;
}

function GridIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
      />
    </svg>
  );
}

function TagIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
      />
    </svg>
  );
}

export function ViewModeToggle({ mode, onChange }: ViewModeToggleProps) {
  return (
    <div className="flex border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => onChange("grid")}
        className={`px-3 py-2 transition-colors ${
          mode === "grid"
            ? "bg-coral text-white"
            : "text-brown-medium hover:bg-gray-100"
        }`}
        title="Grid view"
        aria-label="Grid view"
      >
        <GridIcon className="h-5 w-5" />
      </button>
      <button
        onClick={() => onChange("tags")}
        className={`px-3 py-2 transition-colors ${
          mode === "tags"
            ? "bg-coral text-white"
            : "text-brown-medium hover:bg-gray-100"
        }`}
        title="Group by tags"
        aria-label="Group by tags"
      >
        <TagIcon className="h-5 w-5" />
      </button>
    </div>
  );
}
