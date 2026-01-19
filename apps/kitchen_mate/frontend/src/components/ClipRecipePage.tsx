import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Recipe } from "../types/recipe";
import { clipRecipe, ClipError } from "../api/clip";
import { saveRecipe, RecipeError } from "../api/recipes";
import { RecipeForm } from "./RecipeForm";
import { RecipeCard } from "./RecipeCard";
import { LoadingSpinner } from "./LoadingSpinner";
import { ErrorMessage } from "./ErrorMessage";
import { useRequireAuth } from "../hooks/useRequireAuth";

type ClipState =
  | { status: "idle" }
  | { status: "loading"; url: string; forceLlm: boolean }
  | { status: "success"; url: string; recipe: Recipe }
  | { status: "saving"; url: string; recipe: Recipe }
  | { status: "saved"; url: string; recipe: Recipe; recipeId: string }
  | { status: "error"; url: string; forceLlm: boolean; message: string };

export function ClipRecipePage() {
  const [state, setState] = useState<ClipState>({ status: "idle" });
  const { isAuthorized } = useRequireAuth();
  const navigate = useNavigate();

  const handleSubmit = async (url: string, forceLlm: boolean) => {
    setState({ status: "loading", url, forceLlm });

    try {
      const recipe = await clipRecipe(url, forceLlm);
      setState({ status: "success", url, recipe });
    } catch (error) {
      const message =
        error instanceof ClipError
          ? error.message
          : "An unexpected error occurred";
      setState({ status: "error", url, forceLlm, message });
    }
  };

  const handleRetry = () => {
    if (state.status === "error") {
      handleSubmit(state.url, state.forceLlm);
    }
  };

  const handleSave = async () => {
    if (state.status !== "success") return;

    setState({ status: "saving", url: state.url, recipe: state.recipe });

    try {
      const result = await saveRecipe(state.url);
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
        forceLlm: false,
        message,
      });
    }
  };

  const handleViewSaved = () => {
    if (state.status === "saved") {
      navigate(`/recipes/${state.recipeId}`);
    }
  };

  const handleClipAnother = () => {
    setState({ status: "idle" });
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Add a Recipe
        </h2>
        <p className="text-gray-600">
          Paste a URL from any recipe website to extract and save it.
        </p>
      </div>

      <div className="mb-8">
        <RecipeForm
          onSubmit={handleSubmit}
          isLoading={state.status === "loading"}
        />
      </div>

      {state.status === "loading" && (
        <LoadingSpinner message="Extracting recipe..." />
      )}

      {state.status === "saving" && (
        <LoadingSpinner message="Saving to your collection..." />
      )}

      {state.status === "error" && (
        <ErrorMessage message={state.message} onRetry={handleRetry} />
      )}

      {(state.status === "success" || state.status === "saved") && (
        <div>
          {/* Save/View Actions */}
          <div className="mb-6 p-4 bg-white rounded-lg shadow-sm border border-gray-200">
            {state.status === "success" && isAuthorized && (
              <div className="flex items-center justify-between">
                <p className="text-gray-700">
                  Recipe extracted successfully!
                </p>
                <button
                  onClick={handleSave}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center"
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
                      d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
                    />
                  </svg>
                  Save to Collection
                </button>
              </div>
            )}

            {state.status === "success" && !isAuthorized && (
              <p className="text-gray-700">
                Recipe extracted! Sign in to save it to your collection.
              </p>
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
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    View Recipe
                  </button>
                  <button
                    onClick={handleClipAnother}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
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
