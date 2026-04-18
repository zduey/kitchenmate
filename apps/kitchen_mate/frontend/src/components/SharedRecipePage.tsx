import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getSharedRecipe, saveSharedRecipe, ShareError } from "../api/sharing";
import { LoadingSpinner } from "./LoadingSpinner";
import { useAuthContext } from "../hooks/useAuthContext";
import type { SharedRecipeResponse } from "../types/sharing";
import type { Recipe } from "../types/recipe";

function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

function RecipeDisplay({ recipe }: { recipe: Recipe }) {
  return (
    <>
      {recipe.image && (
        <img
          src={recipe.image}
          alt={recipe.title}
          className="w-full h-64 object-cover"
        />
      )}
      <div className="p-6">
        <h1 className="text-2xl font-bold text-brown-dark mb-4">{recipe.title}</h1>

        {recipe.metadata && (
          <div className="flex flex-wrap gap-4 mb-6 text-sm text-brown-medium">
            {recipe.metadata.author && <span>{recipe.metadata.author}</span>}
            {recipe.metadata.servings && <span>{recipe.metadata.servings} servings</span>}
            {recipe.metadata.prep_time && (
              <span>Prep: {formatTime(recipe.metadata.prep_time)}</span>
            )}
            {recipe.metadata.cook_time && (
              <span>Cook: {formatTime(recipe.metadata.cook_time)}</span>
            )}
            {recipe.metadata.total_time && (
              <span className="font-medium">Total: {formatTime(recipe.metadata.total_time)}</span>
            )}
          </div>
        )}

        {recipe.source_url && (
          <div className="mb-4">
            <a
              href={recipe.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-coral hover:underline"
            >
              {recipe.source_url}
            </a>
          </div>
        )}

        <div className="mb-6">
          <h2 className="text-lg font-semibold text-brown-dark mb-3">Ingredients</h2>
          <ul className="space-y-2">
            {recipe.ingredients.map((ingredient, index) => (
              <li key={index} className="flex items-start">
                <span className="text-coral mr-2">•</span>
                <span>{ingredient.display_text || ingredient.name}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="mb-6">
          <h2 className="text-lg font-semibold text-brown-dark mb-3">Instructions</h2>
          <ol className="space-y-3">
            {recipe.instructions.map((instruction, index) => (
              <li key={index} className="flex">
                <span className="flex-shrink-0 w-6 h-6 bg-coral text-white text-sm rounded-full flex items-center justify-center mr-3 mt-0.5">
                  {index + 1}
                </span>
                <span className="text-brown-medium">{instruction}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </>
  );
}

export function SharedRecipePage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { user } = useAuthContext();

  const [sharedRecipe, setSharedRecipe] = useState<SharedRecipeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    getSharedRecipe(token)
      .then(setSharedRecipe)
      .catch((err) => {
        setError(err instanceof ShareError ? err.message : "Failed to load recipe");
      })
      .finally(() => setLoading(false));
  }, [token]);

  const handleAddToCollection = async () => {
    if (!token) return;
    setSaving(true);
    setSaveError(null);
    try {
      const result = await saveSharedRecipe(token);
      navigate(`/recipes/${result.user_recipe_id}`);
    } catch (err) {
      setSaveError(err instanceof ShareError ? err.message : "Failed to save recipe");
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="py-12">
        <LoadingSpinner message="Loading recipe..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <Link to="/" className="text-coral hover:text-coral-dark">
          Go home
        </Link>
      </div>
    );
  }

  if (!sharedRecipe) return null;

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm text-brown-medium italic">Shared recipe</span>
        {user && (
          <div className="flex flex-col items-end gap-1">
            <button
              onClick={handleAddToCollection}
              disabled={saving}
              className="px-4 py-2 bg-coral text-white rounded-lg text-sm hover:bg-coral-dark disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving..." : "Add to My Collection"}
            </button>
            {saveError && <p className="text-red-600 text-xs">{saveError}</p>}
          </div>
        )}
        {!user && (
          <p className="text-sm text-brown-medium">
            <a href="/add/url" className="text-coral hover:underline">Sign in</a> to add to your collection
          </p>
        )}
      </div>
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <RecipeDisplay recipe={sharedRecipe.recipe} />
      </div>
    </div>
  );
}
