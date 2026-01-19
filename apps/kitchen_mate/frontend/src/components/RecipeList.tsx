import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { UserRecipeSummary } from "../types/recipe";
import { listUserRecipes, RecipeError } from "../api/recipes";
import { RecipeListItem } from "./RecipeListItem";
import { LoadingSpinner } from "./LoadingSpinner";

export function RecipeList() {
  const [recipes, setRecipes] = useState<UserRecipeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const initialLoadDone = useRef(false);

  useEffect(() => {
    if (initialLoadDone.current) return;
    initialLoadDone.current = true;

    listUserRecipes({ limit: 12 })
      .then((response) => {
        setRecipes(response.recipes);
        setNextCursor(response.next_cursor);
        setHasMore(response.has_more);
      })
      .catch((err) => {
        const message =
          err instanceof RecipeError ? err.message : "Failed to load recipes";
        setError(message);
      })
      .finally(() => setLoading(false));
  }, []);

  const fetchRecipes = async (cursor?: string) => {
    try {
      const response = await listUserRecipes({ cursor, limit: 12 });
      if (cursor) {
        setRecipes((prev) => [...prev, ...response.recipes]);
      } else {
        setRecipes(response.recipes);
      }
      setNextCursor(response.next_cursor);
      setHasMore(response.has_more);
      setError(null);
    } catch (err) {
      const message =
        err instanceof RecipeError ? err.message : "Failed to load recipes";
      setError(message);
    }
  };

  const handleLoadMore = async () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    await fetchRecipes(nextCursor);
    setLoadingMore(false);
  };

  if (loading) {
    return (
      <div className="py-12">
        <LoadingSpinner message="Loading your recipes..." />
      </div>
    );
  }

  const handleRetry = async () => {
    setError(null);
    setLoading(true);
    await fetchRecipes();
    setLoading(false);
  };

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={handleRetry}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (recipes.length === 0) {
    return (
      <div className="py-12 text-center">
        <div className="text-gray-400 mb-4">
          <svg
            className="h-16 w-16 mx-auto"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No recipes yet
        </h3>
        <p className="text-gray-600 mb-6">
          Start building your collection by adding a recipe.
        </p>
        <Link
          to="/add"
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <svg
            className="h-5 w-5 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          Add Your First Recipe
        </Link>
      </div>
    );
  }

  return (
    <div>
      {/* Recipe Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {recipes.map((recipe) => (
          <RecipeListItem key={recipe.id} recipe={recipe} />
        ))}
      </div>

      {/* Load More */}
      {hasMore && (
        <div className="mt-8 text-center">
          <button
            onClick={handleLoadMore}
            disabled={loadingMore}
            className="px-6 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loadingMore ? "Loading..." : "Load More"}
          </button>
        </div>
      )}
    </div>
  );
}
