import { useState, useRef, DragEvent, ChangeEvent } from "react";

const ACCEPTED_FILE_TYPES = ".jpg,.jpeg,.png,.gif,.webp,.pdf,.docx,.txt,.md";
const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_DOCUMENT_SIZE = 20 * 1024 * 1024; // 20MB

interface FileDropZoneProps {
  onFileSelect: (file: File) => void;
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

  const validExtensions = ACCEPTED_FILE_TYPES.split(",");
  const ext = "." + file.name.split(".").pop()?.toLowerCase();
  if (!validExtensions.includes(ext)) {
    return `Unsupported file type: ${ext}`;
  }

  return null;
}

export function FileDropZone({ onFileSelect, isLoading }: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    onFileSelect(file);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isLoading) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (isLoading) return;

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
    // Reset input so same file can be selected again
    e.target.value = "";
  };

  const handleClick = () => {
    if (!isLoading) {
      fileInputRef.current?.click();
    }
  };

  return (
    <div className="space-y-2">
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragging ? "border-coral bg-coral bg-opacity-5" : "border-gray-300 hover:border-coral"}
          ${isLoading ? "opacity-50 cursor-not-allowed" : ""}
        `}
      >
        <div className="flex flex-col items-center gap-3">
          <div className={`p-3 rounded-full ${isDragging ? "bg-coral bg-opacity-10" : "bg-gray-100"}`}>
            <svg
              className={`w-8 h-8 ${isDragging ? "text-coral" : "text-gray-400"}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>
          <div>
            <p className="text-brown-dark font-medium">
              {isDragging ? "Drop file here" : "Drop a file here or click to browse"}
            </p>
            <p className="text-sm text-brown-medium mt-1">
              Images: JPG, PNG, GIF, WEBP (max 10MB)
            </p>
            <p className="text-sm text-brown-medium">
              Documents: PDF, DOCX, TXT, MD (max 20MB)
            </p>
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_FILE_TYPES}
          onChange={handleFileChange}
          className="hidden"
          disabled={isLoading}
        />
      </div>
      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}
