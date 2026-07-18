import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { getKitchenRecipe, KitchenError } from "../api/kitchens";
import { LoadingSpinner } from "./LoadingSpinner";
import { CookMode } from "./CookMode";
import type { UserRecipe } from "../types/recipe";

function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

export function KitchenRecipeDetailPage() {
  const { kitchenId, kitchenRecipeId } = useParams<{
    kitchenId: string;
    kitchenRecipeId: string;
  }>();

  const [userRecipe, setUserRecipe] = useState<UserRecipe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cookModeOpen, setCookModeOpen] = useState(false);

  useEffect(() => {
    if (!kitchenId || !kitchenRecipeId) return;
    getKitchenRecipe(kitchenId, kitchenRecipeId)
      .then(setUserRecipe)
      .catch((err) => {
        setError(err instanceof KitchenError ? err.message : "Failed to load recipe");
      })
      .finally(() => setLoading(false));
  }, [kitchenId, kitchenRecipeId]);

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
        <Link to={`/kitchens/${kitchenId}`} className="text-coral hover:text-coral-dark">
          Back to kitchen
        </Link>
      </div>
    );
  }

  if (!userRecipe) return null;

  const recipe = userRecipe.recipe;

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      {recipe.image && (
        <img src={recipe.image} alt={recipe.title} className="w-full h-64 object-cover" />
      )}

      <div className="p-6">
        <div className="mb-4 flex items-start justify-between gap-2">
          <div>
            <Link
              to={`/kitchens/${kitchenId}`}
              className="text-sm text-coral hover:text-coral-dark"
            >
              ← Kitchen
            </Link>
            <h2 className="mt-2 text-2xl font-bold text-brown-dark leading-tight">{recipe.title}</h2>
          </div>
          <button
            onClick={() => setCookModeOpen(true)}
            className="p-2 text-brown-medium hover:text-coral hover:bg-coral hover:bg-opacity-10 rounded shrink-0"
            title="Cook mode"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
          </button>
        </div>

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

        {userRecipe.tags && userRecipe.tags.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-1">
            {userRecipe.tags.map((tag, i) => (
              <span
                key={i}
                className="px-2 py-0.5 bg-gray-100 text-brown-medium text-xs rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {userRecipe.notes && (
          <div className="mb-6 p-3 bg-amber-50 rounded-lg">
            <p className="text-sm text-brown-medium whitespace-pre-wrap">{userRecipe.notes}</p>
          </div>
        )}

        <div className="mb-6">
          <h3 className="text-lg font-semibold text-brown-dark mb-3">Ingredients</h3>
          <ul className="space-y-2">
            {recipe.ingredients.map((ingredient, i) => (
              <li key={i} className="flex items-start">
                <span className="text-coral mr-2">•</span>
                <span>{ingredient.display_text || ingredient.name}</span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-lg font-semibold text-brown-dark mb-3">Instructions</h3>
          <ol className="space-y-3">
            {recipe.instructions.map((step, i) => (
              <li key={i} className="flex">
                <span className="flex-shrink-0 w-6 h-6 bg-coral text-white text-sm rounded-full flex items-center justify-center mr-3 mt-0.5">
                  {i + 1}
                </span>
                <span className="text-brown-medium">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {cookModeOpen && (
        <CookMode recipe={recipe} onClose={() => setCookModeOpen(false)} />
      )}
    </div>
  );
}
