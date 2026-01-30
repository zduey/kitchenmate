import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Recipe } from "../types/recipe";
import { uploadRecipe, ClipError } from "../api/clip";
import { saveRecipe, RecipeError } from "../api/recipes";
import { FileDropZone } from "./FileDropZone";
import { RecipeCard } from "./RecipeCard";
import { LoadingSpinner } from "./LoadingSpinner";
import { ErrorMessage, ErrorType } from "./ErrorMessage";
import { useRequireAuth } from "../hooks/useRequireAuth";
import { useIsPro } from "../hooks/usePermission";

type PageState =
  | { status: "idle" }
  | { status: "extracting"; filename: string }
  | { status: "extracted"; filename: string; recipe: Recipe; parsingMethod: string }
  | { status: "saving"; filename: string; recipe: Recipe; parsingMethod: string }
  | { status: "saved"; filename: string; recipe: Recipe; recipeId: string }
  | { status: "error"; filename: string; message: string; errorType: ErrorType };

export function AddFromUploadPage() {
  const [state, setState] = useState<PageState>({ status: "idle" });
  const { isAuthorized } = useRequireAuth();
  const isPro = useIsPro();
  const navigate = useNavigate();

  const handleFileSelect = async (file: File) => {
    setState({ status: "extracting", filename: file.name });

    try {
      const result = await uploadRecipe(file);
      setState({
        status: "extracted",
        filename: file.name,
        recipe: result.recipe,
        parsingMethod: result.parsing_method,
      });
    } catch (error) {
      let message = "Failed to extract recipe from file";
      let errorType: ErrorType = "generic";

      if (error instanceof ClipError) {
        message = error.message;
        if (error.isUpgradeRequired) {
          errorType = "upgrade_required";
        } else if (error.isSubscriptionExpired) {
          errorType = "subscription_expired";
        }
      }

      setState({ status: "error", filename: file.name, message, errorType });
    }
  };

  const handleSave = async () => {
    if (state.status !== "extracted") return;

    setState({
      status: "saving",
      filename: state.filename,
      recipe: state.recipe,
      parsingMethod: state.parsingMethod,
    });

    try {
      const result = await saveRecipe({
        sourceType: "upload",
        recipe: state.recipe,
        parsingMethod: state.parsingMethod,
      });
      setState({
        status: "saved",
        filename: state.filename,
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
        filename: state.filename,
        message,
        errorType: "generic",
      });
    }
  };

  const handleViewSaved = () => {
    if (state.status === "saved") {
      navigate(`/recipes/${state.recipeId}`);
    }
  };

  const handleAddAnother = () => {
    setState({ status: "idle" });
  };

  const isLoading = state.status === "extracting" || state.status === "saving";

  // Show upgrade prompt for non-Pro users
  if (!isPro) {
    return (
      <div>
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-brown-dark mb-2">
            Add Recipe from File
          </h2>
          <p className="text-brown-medium">
            Upload an image or document containing a recipe.
          </p>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 text-center">
          <div className="flex justify-center mb-3">
            <span className="inline-flex items-center justify-center w-12 h-12 bg-amber-100 rounded-full">
              <svg
                className="w-6 h-6 text-amber-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
            </span>
          </div>
          <h3 className="text-lg font-semibold text-amber-800 mb-2">
            Pro Feature
          </h3>
          <p className="text-amber-700 mb-4">
            File upload requires a Pro subscription to use AI-powered recipe extraction.
          </p>
          <Link
            to="/add/url"
            className="inline-block px-4 py-2 text-sm font-medium text-amber-700 border border-amber-300 rounded-lg hover:bg-amber-100 transition-colors"
          >
            Extract from URL instead
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-brown-dark mb-2">
          Add Recipe from File
        </h2>
        <p className="text-brown-medium">
          Upload an image or document containing a recipe.
        </p>
      </div>

      {/* File Drop Zone - only show when idle or error */}
      {(state.status === "idle" || state.status === "error") && (
        <div className="mb-8">
          <FileDropZone onFileSelect={handleFileSelect} isLoading={isLoading} />
        </div>
      )}

      {/* Loading States */}
      {state.status === "extracting" && (
        <LoadingSpinner message={`Extracting recipe from ${state.filename}...`} />
      )}

      {state.status === "saving" && (
        <LoadingSpinner message="Saving to your collection..." />
      )}

      {/* Error State */}
      {state.status === "error" && (
        <ErrorMessage message={state.message} errorType={state.errorType} />
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
                    Upload Another
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
                    Upload Another
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
