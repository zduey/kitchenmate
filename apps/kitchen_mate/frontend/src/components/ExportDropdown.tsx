import { useState, useRef, useEffect } from "react";
import { Recipe, OutputFormat } from "../types/recipe";
import {
  convertRecipe,
  exportAsJson,
  triggerDownload,
  getFileExtension,
  ClipError,
} from "../api/clip";

interface ExportDropdownProps {
  recipe: Recipe;
}

const FORMAT_OPTIONS: { value: OutputFormat; label: string }[] = [
  { value: "json", label: "JSON" },
  { value: "text", label: "Text" },
  { value: "markdown", label: "Markdown" },
];

export function ExportDropdown({ recipe }: ExportDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [exporting, setExporting] = useState<OutputFormat | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleExport = async (format: OutputFormat) => {
    setExporting(format);
    setIsOpen(false);

    try {
      const extension = getFileExtension(format);
      const filename = `${recipe.title.toLowerCase().replace(/\s+/g, "-")}.${extension}`;

      let blob: Blob;
      if (format === "json") {
        blob = exportAsJson(recipe);
      } else {
        blob = await convertRecipe(recipe, format);
      }

      triggerDownload(blob, filename);
    } catch (error) {
      console.error("Export failed:", error);
      alert(
        error instanceof ClipError ? error.message : "Failed to export recipe"
      );
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={exporting !== null}
        className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {exporting ? (
          <>
            <svg
              className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Exporting...
          </>
        ) : (
          <>
            <svg
              className="mr-2 h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Export
            <svg
              className="ml-2 h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 bottom-full mb-2 w-40 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10">
          {FORMAT_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => handleExport(option.value)}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 transition-colors"
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
