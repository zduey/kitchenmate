import { useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Recipe } from "../types/recipe";
import { clipRecipe, ClipError } from "../api/clip";
import { saveRecipe, RecipeError } from "../api/recipes";
import { RecipeCard } from "./RecipeCard";
import { LoadingSpinner } from "./LoadingSpinner";
import { ErrorMessage } from "./ErrorMessage";
import { useRequireAuth } from "../hooks/useRequireAuth";

type PageState =
  | { status: "idle" }
  | { status: "extracting"; url: string }
  | { status: "extracted"; url: string; recipe: Recipe }
  | { status: "saving"; url: string; recipe: Recipe }
  | { status: "saved"; url: string; recipe: Recipe; recipeId: string }
  | { status: "error"; url: string; message: string };

export function AddFromUrlPage() {
  const [state, setState] = useState<PageState>({ status: "idle" });
  const [url, setUrl] = useState("");
  const { isAuthorized } = useRequireAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmedUrl = url.trim();
    if (!trimmedUrl) return;

    setState({ status: "extracting", url: trimmedUrl });

    try {
      const recipe = await clipRecipe(trimmedUrl);
      setState({ status: "extracted", url: trimmedUrl, recipe });
    } catch (error) {
      const message =
        error instanceof ClipError
          ? error.message
          : "An unexpected error occurred";
      setState({ status: "error", url: trimmedUrl, message });
    }
  };

  const handleRetry = () => {
    if (state.status === "error") {
      setUrl(state.url);
      setState({ status: "idle" });
    }
  };

  const handleSave = async () => {
    if (state.status !== "extracted") return;

    setState({ status: "saving", url: state.url, recipe: state.recipe });

    try {
      const result = await saveRecipe({ url: state.url });
      setState({
        status: "saved",
        url: state.url,
        recipe: state.recipe,
        recipeId: result.user_recipe_id,
      });
    } catch (error) {
      const message =
        error instanceof RecipeError
          ? error.message
          : "Failed to save recipe";
      setState({
        status: "error",
        url: state.url,
        message,
      });
    }
  };

  const handleViewSaved = () => {
    if (state.status === "saved") {
      navigate(`/recipes/${state.recipeId}`);
    }
  };

  const handleAddAnother = () => {
    setUrl("");
    setState({ status: "idle" });
  };

  const isLoading = state.status === "extracting" || state.status === "saving";

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-brown-dark mb-2">
          Add Recipe from URL
        </h2>
        <p className="text-brown-medium">
          Paste a link to any recipe webpage to extract it.
        </p>
      </div>

      {/* URL Input Form */}
      <form onSubmit={handleSubmit} className="mb-8">
        <div className="flex gap-3">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/recipe..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
            disabled={isLoading}
            required
          />
          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="px-6 py-2 bg-coral text-white font-medium rounded-lg hover:bg-coral-dark focus:outline-none focus:ring-2 focus:ring-coral focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {state.status === "extracting" ? "Extracting..." : "Extract Recipe"}
          </button>
        </div>
      </form>

      {/* Loading States */}
      {state.status === "extracting" && (
        <LoadingSpinner message="Extracting recipe..." />
      )}

      {state.status === "saving" && (
        <LoadingSpinner message="Saving to your collection..." />
      )}

      {/* Error State */}
      {state.status === "error" && (
        <ErrorMessage message={state.message} onRetry={handleRetry} />
      )}

      {/* Success States */}
      {(state.status === "extracted" || state.status === "saved") && (
        <div>
          {/* Status message and actions */}
          <div className="mb-6 p-4 bg-white rounded-lg shadow-sm border border-gray-200">
            {state.status === "extracted" && (
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <p className="text-brown-dark font-medium">Recipe extracted!</p>
                  <p className="text-brown-medium text-sm">
                    {isAuthorized
                      ? "Save it to your collection or export it below."
                      : "Export it below, or sign in to save it to your collection."}
                  </p>
                </div>
                <div className="flex gap-3">
                  {isAuthorized && (
                    <button
                      onClick={handleSave}
                      className="px-4 py-2 text-sm bg-coral text-white rounded-lg hover:bg-coral-dark"
                    >
                      Save to Collection
                    </button>
                  )}
                  <button
                    onClick={handleAddAnother}
                    className="px-4 py-2 text-sm border border-gray-300 text-brown-medium rounded-lg hover:bg-gray-50"
                  >
                    Add Another
                  </button>
                </div>
              </div>
            )}

            {state.status === "saved" && (
              <div className="flex items-center justify-between">
                <p className="text-green-700 flex items-center">
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
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  Recipe saved to your collection!
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={handleViewSaved}
                    className="px-4 py-2 bg-coral text-white rounded-lg hover:bg-coral-dark"
                  >
                    View Recipe
                  </button>
                  <button
                    onClick={handleAddAnother}
                    className="px-4 py-2 border border-gray-300 text-brown-medium rounded-lg hover:bg-gray-50"
                  >
                    Add Another
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Recipe Preview */}
          <RecipeCard recipe={state.recipe} />
        </div>
      )}
    </div>
  );
}
