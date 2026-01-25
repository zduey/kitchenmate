import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Recipe } from "../types/recipe";
import { uploadRecipe, ClipError } from "../api/clip";
import { saveRecipe, RecipeError } from "../api/recipes";
import { FileDropZone } from "./FileDropZone";
import { RecipeCard } from "./RecipeCard";
import { LoadingSpinner } from "./LoadingSpinner";
import { ErrorMessage } from "./ErrorMessage";
import { useRequireAuth } from "../hooks/useRequireAuth";

type PageState =
  | { status: "idle" }
  | { status: "extracting"; filename: string }
  | { status: "extracted"; filename: string; recipe: Recipe; parsingMethod: string }
  | { status: "saving"; filename: string; recipe: Recipe; parsingMethod: string }
  | { status: "saved"; filename: string; recipe: Recipe; recipeId: string }
  | { status: "error"; filename: string; message: string };

export function AddFromUploadPage() {
  const [state, setState] = useState<PageState>({ status: "idle" });
  const { isAuthorized } = useRequireAuth();
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
      const message =
        error instanceof ClipError
          ? error.message
          : "Failed to extract recipe from file";
      setState({ status: "error", filename: file.name, message });
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
        <ErrorMessage message={state.message} />
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
