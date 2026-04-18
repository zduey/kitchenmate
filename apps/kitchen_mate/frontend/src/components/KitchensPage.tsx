import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { listKitchens, createKitchen, KitchenError } from "../api/kitchens";
import { useAuthContext } from "../hooks/useAuthContext";
import { useRequireAuth } from "../hooks/useRequireAuth";
import { LoadingSpinner } from "./LoadingSpinner";
import type { KitchenSummary } from "../types/kitchen";

export function KitchensPage() {
  const { isAuthEnabled } = useAuthContext();
  const { isAuthorized } = useRequireAuth();
  const [kitchens, setKitchens] = useState<KitchenSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!isAuthEnabled || !isAuthorized) {
      setLoading(false);
      return;
    }
    listKitchens()
      .then(setKitchens)
      .catch((err) => setError(err instanceof KitchenError ? err.message : "Failed to load kitchens"))
      .finally(() => setLoading(false));
  }, [isAuthEnabled, isAuthorized]);

  if (!isAuthEnabled) {
    return (
      <div className="py-12 text-center">
        <p className="text-brown-medium">Kitchens are only available in multi-user mode.</p>
      </div>
    );
  }

  if (!isAuthorized) {
    return (
      <div className="py-12 text-center">
        <p className="text-brown-medium">Sign in to use Kitchens.</p>
      </div>
    );
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const kitchen = await createKitchen(newName.trim());
      setKitchens((prev) => [kitchen, ...prev]);
      setNewName("");
      setShowCreate(false);
    } catch (err) {
      setError(err instanceof KitchenError ? err.message : "Failed to create kitchen");
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="py-12">
        <LoadingSpinner message="Loading kitchens..." />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-brown-dark">My Kitchens</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-coral text-white rounded-lg text-sm hover:bg-coral-dark transition-colors"
        >
          Create Kitchen
        </button>
      </div>

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      {showCreate && (
        <form onSubmit={handleCreate} className="mb-6 p-4 border border-gray-200 rounded-lg bg-white">
          <h2 className="text-sm font-medium text-brown-dark mb-3">New Kitchen</h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Kitchen name"
              maxLength={100}
              className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-coral"
              autoFocus
            />
            <button
              type="submit"
              disabled={creating || !newName.trim()}
              className="px-4 py-2 bg-coral text-white rounded text-sm hover:bg-coral-dark disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create"}
            </button>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="px-3 py-2 text-brown-medium hover:text-brown-dark text-sm"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {kitchens.length === 0 ? (
        <div className="py-12 text-center">
          <p className="text-brown-medium mb-4">You don't belong to any kitchens yet.</p>
          {!showCreate && (
            <button
              onClick={() => setShowCreate(true)}
              className="text-coral hover:underline text-sm"
            >
              Create your first kitchen
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {kitchens.map((kitchen) => (
            <Link
              key={kitchen.id}
              to={`/kitchens/${kitchen.id}`}
              className="block p-4 bg-white border border-gray-200 rounded-lg hover:border-coral hover:shadow-sm transition-all"
            >
              <div className="flex justify-between items-center">
                <h2 className="font-medium text-brown-dark">{kitchen.name}</h2>
                <span className="text-sm text-brown-medium">
                  {kitchen.member_count} member{kitchen.member_count !== 1 ? "s" : ""}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
