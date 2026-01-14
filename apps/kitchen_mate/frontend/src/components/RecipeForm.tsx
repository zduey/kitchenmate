import { useState, FormEvent, useRef, useEffect } from "react";

interface RecipeFormProps {
  onSubmit: (url: string, forceLlm: boolean) => void;
  isLoading: boolean;
}

export function RecipeForm({ onSubmit, isLoading }: RecipeFormProps) {
  const [url, setUrl] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      onSubmit(url.trim(), false);
    }
  };

  const handleClipWithAi = () => {
    if (url.trim()) {
      onSubmit(url.trim(), true);
      setDropdownOpen(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <input
        type="url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Enter recipe URL..."
        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        disabled={isLoading}
        required
      />
      <div className="relative" ref={dropdownRef}>
        <div className="flex">
          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="px-6 py-2 bg-blue-600 text-white font-medium rounded-l-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? "Clipping..." : "Clip"}
          </button>
          <button
            type="button"
            disabled={isLoading}
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="px-2 py-2 bg-blue-600 text-white font-medium rounded-r-lg border-l border-blue-500 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="More clip options"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
        {dropdownOpen && (
          <div className="absolute right-0 mt-1 w-40 bg-white rounded-lg shadow-lg border border-gray-200 z-10">
            <button
              type="button"
              onClick={handleClipWithAi}
              disabled={!url.trim()}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Clip with AI
            </button>
          </div>
        )}
      </div>
    </form>
  );
}
