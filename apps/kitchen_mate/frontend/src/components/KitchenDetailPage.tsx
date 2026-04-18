import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getKitchen,
  listKitchenRecipes,
  addMember,
  removeMember,
  removeKitchenRecipe,
  KitchenError,
} from "../api/kitchens";
import { useAuthContext } from "../hooks/useAuthContext";
import { LoadingSpinner } from "./LoadingSpinner";
import { KitchenRecipeListItem } from "./KitchenRecipeListItem";
import type { KitchenDetail, KitchenRecipe } from "../types/kitchen";

export function KitchenDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuthContext();

  const [kitchen, setKitchen] = useState<KitchenDetail | null>(null);
  const [recipes, setRecipes] = useState<KitchenRecipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Member management
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [inviteMessage, setInviteMessage] = useState<string | null>(null);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [removingMember, setRemovingMember] = useState<string | null>(null);

  // Recipe management
  const [removingRecipe, setRemovingRecipe] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([getKitchen(id), listKitchenRecipes(id)])
      .then(([k, r]) => {
        setKitchen(k);
        setRecipes(r.recipes);
      })
      .catch((err) => setError(err instanceof KitchenError ? err.message : "Failed to load kitchen"))
      .finally(() => setLoading(false));
  }, [id]);

  const isAdmin = kitchen?.members.find((m) => m.user_id === user?.id)?.role === "admin";

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !inviteEmail.trim()) return;
    setInviting(true);
    setInviteError(null);
    setInviteMessage(null);
    try {
      const result = await addMember(id, inviteEmail.trim());
      setInviteMessage(result.message);
      setInviteEmail("");
      if (result.added) {
        const updated = await getKitchen(id);
        if (updated) setKitchen(updated);
      }
    } catch (err) {
      setInviteError(err instanceof KitchenError ? err.message : "Failed to add member");
    } finally {
      setInviting(false);
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!id) return;
    setRemovingMember(userId);
    try {
      await removeMember(id, userId);
      setKitchen((prev) =>
        prev ? { ...prev, members: prev.members.filter((m) => m.user_id !== userId) } : prev
      );
    } catch (err) {
      setError(err instanceof KitchenError ? err.message : "Failed to remove member");
    } finally {
      setRemovingMember(null);
    }
  };

  const handleRemoveRecipe = async (kitchenRecipeId: string) => {
    if (!id) return;
    setRemovingRecipe(kitchenRecipeId);
    try {
      await removeKitchenRecipe(id, kitchenRecipeId);
      setRecipes((prev) => prev.filter((r) => r.id !== kitchenRecipeId));
    } catch (err) {
      setError(err instanceof KitchenError ? err.message : "Failed to remove recipe");
    } finally {
      setRemovingRecipe(null);
    }
  };

  if (loading) {
    return (
      <div className="py-12">
        <LoadingSpinner message="Loading kitchen..." />
      </div>
    );
  }

  if (error && !kitchen) {
    return (
      <div className="py-12 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <Link to="/kitchens" className="text-coral hover:text-coral-dark">Back to Kitchens</Link>
      </div>
    );
  }

  if (!kitchen) return null;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/kitchens" className="text-coral hover:text-coral-dark text-sm">
          ← Kitchens
        </Link>
      </div>

      <h1 className="text-2xl font-bold text-brown-dark">{kitchen.name}</h1>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      {/* Members section */}
      <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
        <h2 className="text-base font-semibold text-brown-dark mb-4">Members</h2>
        <ul className="space-y-2 mb-4">
          {kitchen.members.map((member) => (
            <li key={member.user_id} className="flex items-center justify-between">
              <div>
                <span className="text-sm text-brown-dark">{member.email ?? member.user_id}</span>
                {member.role === "admin" && (
                  <span className="ml-2 text-xs px-1.5 py-0.5 bg-coral bg-opacity-10 text-coral-dark rounded">
                    admin
                  </span>
                )}
              </div>
              {isAdmin && member.user_id !== user?.id && (
                <button
                  onClick={() => handleRemoveMember(member.user_id)}
                  disabled={removingMember === member.user_id}
                  className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
                >
                  {removingMember === member.user_id ? "Removing..." : "Remove"}
                </button>
              )}
            </li>
          ))}
        </ul>

        {isAdmin && (
          <form onSubmit={handleInvite} className="flex gap-2">
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="Add member by email"
              className="flex-1 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-coral"
            />
            <button
              type="submit"
              disabled={inviting || !inviteEmail.trim()}
              className="px-3 py-1.5 bg-coral text-white rounded text-sm hover:bg-coral-dark disabled:opacity-50"
            >
              {inviting ? "Adding..." : "Add"}
            </button>
          </form>
        )}
        {inviteMessage && <p className="text-green-600 text-xs mt-2">{inviteMessage}</p>}
        {inviteError && <p className="text-red-600 text-xs mt-2">{inviteError}</p>}
      </section>

      {/* Recipes section */}
      <section>
        <h2 className="text-base font-semibold text-brown-dark mb-3">
          Shared Recipes ({recipes.length})
        </h2>

        {recipes.length === 0 ? (
          <p className="text-brown-medium text-sm py-4">
            No recipes shared yet. Share a recipe from your collection using the kitchen icon on any recipe.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {recipes.map((recipe) => (
              <KitchenRecipeListItem
                key={recipe.id}
                recipe={recipe}
                kitchenName={kitchen.name}
                onRemove={() => handleRemoveRecipe(recipe.id)}
                removing={removingRecipe === recipe.id}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
