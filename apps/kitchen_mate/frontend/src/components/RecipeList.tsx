import { useState, useEffect, useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import { UserRecipeSummary } from "../types/recipe";
import { listUserRecipes, RecipeError } from "../api/recipes";
import { RecipeListItem } from "./RecipeListItem";
import { LoadingSpinner } from "./LoadingSpinner";
import { TagGroupsView } from "./TagGroupsView";

interface RecipeListProps {
  viewMode?: "grid" | "tags";
  tagFilter?: string | null;
  onTagSelect?: (tag: string | null) => void;
}

export function RecipeList({
  viewMode = "grid",
  tagFilter = null,
  onTagSelect,
}: RecipeListProps) {
  const [recipes, setRecipes] = useState<UserRecipeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  // Compute tag counts from loaded recipes
  const tagCounts = useMemo(() => {
    const counts = new Map<string, number>();
    let untagged = 0;

    for (const recipe of recipes) {
      if (!recipe.tags || recipe.tags.length === 0) {
        untagged++;
      } else {
        for (const tag of recipe.tags) {
          counts.set(tag, (counts.get(tag) || 0) + 1);
        }
      }
    }

    return { tags: counts, untagged };
  }, [recipes]);

  const fetchRecipes = useCallback(async (cursor?: string, filter?: string | null, isInitial?: boolean) => {
    if (isInitial) {
      setLoading(true);
      setRecipes([]);
      setNextCursor(null);
      setHasMore(false);
    }

    try {
      // Don't pass tag filter to API for untagged - we'll filter client-side
      const apiFilter = filter && filter !== "__untagged__" ? [filter] : undefined;
      const response = await listUserRecipes({ cursor, limit: 12, tags: apiFilter });

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
    } finally {
      if (isInitial) {
        setLoading(false);
      }
    }
  }, []);

  // Initial load and refetch when tagFilter changes
  useEffect(() => {
    fetchRecipes(undefined, tagFilter, true);
  }, [tagFilter, fetchRecipes]);

  const handleLoadMore = async () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    await fetchRecipes(nextCursor, tagFilter);
    setLoadingMore(false);
  };

  const handleRetry = async () => {
    setError(null);
    setLoading(true);
    await fetchRecipes(undefined, tagFilter);
    setLoading(false);
  };

  // Filter for untagged recipes client-side
  const displayedRecipes = useMemo(() => {
    if (tagFilter === "__untagged__") {
      return recipes.filter((r) => !r.tags || r.tags.length === 0);
    }
    return recipes;
  }, [recipes, tagFilter]);

  if (loading) {
    return (
      <div className="py-12">
        <LoadingSpinner message="Loading your recipes..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={handleRetry}
          className="px-4 py-2 bg-coral text-white rounded-lg hover:bg-coral-dark"
        >
          Try Again
        </button>
      </div>
    );
  }

  // Show tag groups view when in tags mode and no filter active
  if (viewMode === "tags" && !tagFilter && onTagSelect) {
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
          <h3 className="text-lg font-medium text-brown-dark mb-2">
            No recipes yet
          </h3>
          <p className="text-brown-medium mb-6">
            Start building your collection by adding a recipe.
          </p>
          <Link
            to="/add/url"
            className="inline-flex items-center px-4 py-2 bg-coral text-white rounded-lg hover:bg-coral-dark"
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
      <TagGroupsView
        tagCounts={tagCounts}
        onTagSelect={onTagSelect}
        hasMore={hasMore}
        onLoadMore={handleLoadMore}
        loadingMore={loadingMore}
      />
    );
  }

  // Grid view (default)
  if (displayedRecipes.length === 0) {
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
        <h3 className="text-lg font-medium text-brown-dark mb-2">
          {tagFilter ? "No recipes found" : "No recipes yet"}
        </h3>
        <p className="text-brown-medium mb-6">
          {tagFilter
            ? `No recipes with this tag.`
            : "Start building your collection by adding a recipe."}
        </p>
        {!tagFilter && (
          <Link
            to="/add/url"
            className="inline-flex items-center px-4 py-2 bg-coral text-white rounded-lg hover:bg-coral-dark"
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
        )}
      </div>
    );
  }

  return (
    <div>
      {/* Recipe Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {displayedRecipes.map((recipe) => (
          <RecipeListItem key={recipe.id} recipe={recipe} />
        ))}
      </div>

      {/* Load More */}
      {hasMore && (
        <div className="mt-8 text-center">
          <button
            onClick={handleLoadMore}
            disabled={loadingMore}
            className="px-6 py-2 bg-white border border-gray-300 text-brown-medium rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loadingMore ? "Loading..." : "Load More"}
          </button>
        </div>
      )}
    </div>
  );
}
