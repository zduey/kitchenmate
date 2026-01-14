import { useState, FormEvent } from "react";

interface RecipeFormProps {
  onSubmit: (url: string) => void;
  isLoading: boolean;
}

export function RecipeForm({ onSubmit, isLoading }: RecipeFormProps) {
  const [url, setUrl] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      onSubmit(url.trim());
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
      <button
        type="submit"
        disabled={isLoading || !url.trim()}
        className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? "Clipping..." : "Clip"}
      </button>
    </form>
  );
}
