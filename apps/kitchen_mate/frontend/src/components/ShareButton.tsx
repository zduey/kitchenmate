import { useState } from "react";
import { createShare, revokeShare, ShareError } from "../api/sharing";
import type { CreateShareResponse } from "../types/sharing";

interface ShareButtonProps {
  recipeId: string;
}

export function ShareButton({ recipeId }: ShareButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [share, setShare] = useState<CreateShareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleOpen = async () => {
    setIsOpen(true);
    if (share) return;
    setLoading(true);
    setError(null);
    try {
      const result = await createShare(recipeId);
      setShare(result);
    } catch (err) {
      setError(err instanceof ShareError ? err.message : "Failed to generate link");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!share) return;
    await navigator.clipboard.writeText(share.share_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRevoke = async () => {
    if (!share) return;
    setLoading(true);
    setError(null);
    try {
      await revokeShare(recipeId);
      setShare(null);
      setIsOpen(false);
    } catch (err) {
      setError(err instanceof ShareError ? err.message : "Failed to revoke link");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        onClick={handleOpen}
        className="p-2 text-brown-medium hover:text-coral hover:bg-coral hover:bg-opacity-10 rounded"
        title="Share recipe"
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
          />
        </svg>
      </button>

      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => e.target === e.currentTarget && setIsOpen(false)}
        >
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-brown-dark">Share Recipe</h3>
              <button
                onClick={() => setIsOpen(false)}
                className="text-brown-medium hover:text-brown-dark"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {loading && (
              <p className="text-brown-medium text-sm">Generating link...</p>
            )}

            {error && (
              <p className="text-red-600 text-sm">{error}</p>
            )}

            {!loading && share && (
              <>
                <p className="text-sm text-brown-medium mb-3">
                  Anyone with this link can view the recipe without signing in.
                </p>
                <div className="flex gap-2 mb-4">
                  <input
                    type="text"
                    readOnly
                    value={share.share_url}
                    className="flex-1 text-sm border border-gray-300 rounded px-3 py-2 bg-gray-50 text-brown-dark"
                  />
                  <button
                    onClick={handleCopy}
                    className="px-3 py-2 bg-coral text-white rounded text-sm hover:bg-coral-dark transition-colors"
                  >
                    {copied ? "Copied!" : "Copy"}
                  </button>
                </div>
                <button
                  onClick={handleRevoke}
                  disabled={loading}
                  className="text-sm text-red-500 hover:text-red-700"
                >
                  Revoke link
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
