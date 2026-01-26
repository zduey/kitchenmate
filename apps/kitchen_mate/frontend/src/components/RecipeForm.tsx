import { useState, FormEvent, useRef, useEffect, ChangeEvent } from "react";

const ACCEPTED_FILE_TYPES = ".jpg,.jpeg,.png,.gif,.webp,.pdf,.docx,.txt,.md";
const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_DOCUMENT_SIZE = 20 * 1024 * 1024; // 20MB

interface RecipeFormProps {
  onSubmit: (url: string, forceLlm: boolean) => void;
  onUpload: (file: File) => void;
  isLoading: boolean;
}

function isImageFile(file: File): boolean {
  return file.type.startsWith("image/") || /\.(jpg|jpeg|png|gif|webp)$/i.test(file.name);
}

function validateFile(file: File): string | null {
  const maxSize = isImageFile(file) ? MAX_IMAGE_SIZE : MAX_DOCUMENT_SIZE;
  const maxSizeMB = maxSize / (1024 * 1024);

  if (file.size > maxSize) {
    return `File size exceeds ${maxSizeMB}MB limit`;
  }

  return null;
}

export function RecipeForm({ onSubmit, onUpload, isLoading }: RecipeFormProps) {
  const [url, setUrl] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      setFileError(null);
      onSubmit(url.trim(), false);
    }
  };

  const handleClipWithAi = () => {
    if (url.trim()) {
      setFileError(null);
      onSubmit(url.trim(), true);
      setDropdownOpen(false);
    }
  };

  const handleUploadClick = () => {
    setDropdownOpen(false);
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input so same file can be selected again
    e.target.value = "";

    const error = validateFile(file);
    if (error) {
      setFileError(error);
      return;
    }

    setFileError(null);
    onUpload(file);
  };

  return (
    <div className="space-y-2">
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Enter recipe URL..."
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
          disabled={isLoading}
          required
        />
        <div className="relative" ref={dropdownRef}>
          <div className="flex">
            <button
              type="submit"
              disabled={isLoading || !url.trim()}
              className="px-6 py-2 bg-coral text-white font-medium rounded-l-lg hover:bg-coral-dark focus:outline-none focus:ring-2 focus:ring-coral focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? "Clipping..." : "Clip"}
            </button>
            <button
              type="button"
              disabled={isLoading}
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="px-2 py-2 bg-coral text-white font-medium rounded-r-lg border-l border-coral-dark hover:bg-coral-dark focus:outline-none focus:ring-2 focus:ring-coral focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="More clip options"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
          {dropdownOpen && (
            <div className="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-10">
              <button
                type="button"
                onClick={handleClipWithAi}
                disabled={!url.trim()}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 rounded-t-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Clip with AI
              </button>
              <button
                type="button"
                onClick={handleUploadClick}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 rounded-b-lg border-t border-gray-100"
              >
                Upload image or file
              </button>
            </div>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_FILE_TYPES}
          onChange={handleFileChange}
          className="hidden"
          disabled={isLoading}
        />
      </form>
      {fileError && (
        <p className="text-sm text-red-600">{fileError}</p>
      )}
    </div>
  );
}
