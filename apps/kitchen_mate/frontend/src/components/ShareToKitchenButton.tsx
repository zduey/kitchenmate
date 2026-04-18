import { useState } from "react";
import { listKitchens, shareRecipeToKitchen, KitchenError } from "../api/kitchens";
import { useAuthContext } from "../hooks/useAuthContext";
import type { KitchenSummary } from "../types/kitchen";

interface ShareToKitchenButtonProps {
  recipeId: string;
}

export function ShareToKitchenButton({ recipeId }: ShareToKitchenButtonProps) {
  const { isAuthEnabled } = useAuthContext();
  const [isOpen, setIsOpen] = useState(false);
  const [kitchens, setKitchens] = useState<KitchenSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [sharing, setSharing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sharedKitchens, setSharedKitchens] = useState<Set<string>>(new Set());

  if (!isAuthEnabled) return null;

  const handleOpen = async () => {
    setIsOpen(true);
    setLoading(true);
    setError(null);
    try {
      const result = await listKitchens();
      setKitchens(result);
    } catch (err) {
      setError(err instanceof KitchenError ? err.message : "Failed to load kitchens");
    } finally {
      setLoading(false);
    }
  };

  const handleShare = async (kitchen: KitchenSummary) => {
    setSharing(kitchen.id);
    setError(null);
    try {
      await shareRecipeToKitchen(kitchen.id, recipeId);
      setSharedKitchens((prev) => new Set(prev).add(kitchen.id));
    } catch (err) {
      const msg = err instanceof KitchenError ? err.message : "Failed to share";
      setError(msg);
    } finally {
      setSharing(null);
    }
  };

  return (
    <>
      <button
        onClick={handleOpen}
        className="p-2 text-brown-medium hover:text-coral hover:bg-coral hover:bg-opacity-10 rounded"
        title="Share to kitchen"
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
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
              <h3 className="text-lg font-semibold text-brown-dark">Share to Kitchen</h3>
              <button
                onClick={() => setIsOpen(false)}
                className="text-brown-medium hover:text-brown-dark"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

            {loading && <p className="text-brown-medium text-sm">Loading kitchens...</p>}

            {!loading && kitchens.length === 0 && (
              <p className="text-brown-medium text-sm">
                You don't belong to any kitchens yet.{" "}
                <a href="/kitchens" className="text-coral hover:underline">Create one</a>.
              </p>
            )}

            {!loading && kitchens.length > 0 && (
              <ul className="space-y-2">
                {kitchens.map((kitchen) => {
                  const isShared = sharedKitchens.has(kitchen.id);
                  return (
                    <li
                      key={kitchen.id}
                      className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
                    >
                      <div>
                        <p className="text-sm font-medium text-brown-dark">{kitchen.name}</p>
                        <p className="text-xs text-brown-medium">{kitchen.member_count} member{kitchen.member_count !== 1 ? "s" : ""}</p>
                      </div>
                      <button
                        onClick={() => handleShare(kitchen)}
                        disabled={isShared || sharing === kitchen.id}
                        className={`px-3 py-1.5 text-sm rounded transition-colors ${
                          isShared
                            ? "bg-green-100 text-green-700 cursor-default"
                            : "bg-coral text-white hover:bg-coral-dark"
                        }`}
                      >
                        {isShared ? "Shared" : sharing === kitchen.id ? "Sharing..." : "Share"}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </>
  );
}
