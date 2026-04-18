import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Recipe } from "../types/recipe";
import { saveRecipe, uploadRecipeThumbnail, RecipeError } from "../api/recipes";
import { RecipeEditor } from "./RecipeEditor";
import { LoadingSpinner } from "./LoadingSpinner";
import { ErrorMessage } from "./ErrorMessage";
import { useRequireAuth } from "../hooks/useRequireAuth";
import { useAuthContext } from "../hooks/useAuthContext";

const EMPTY_RECIPE: Recipe = {
  title: "",
  ingredients: [{ name: "", display_text: "" }],
  instructions: [""],
};

export function AddManualPage() {
  const [recipe, setRecipe] = useState<Recipe>(EMPTY_RECIPE);
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { isAuthorized } = useRequireAuth();
  const { isAuthEnabled } = useAuthContext();

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
    setImageFile(file);
    setImagePreviewUrl(URL.createObjectURL(file));
  };

  const handleRemoveImage = () => {
    if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
    setImageFile(null);
    setImagePreviewUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSave = async () => {
    // Validate required fields
    if (!recipe.title.trim()) {
      setError("Recipe title is required");
      return;
    }

    const hasIngredients = recipe.ingredients.some(
      (ing) => (ing.display_text || ing.name).trim()
    );
    if (!hasIngredients) {
      setError("At least one ingredient is required");
      return;
    }

    const hasInstructions = recipe.instructions.some((inst) => inst.trim());
    if (!hasInstructions) {
      setError("At least one instruction is required");
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      // Clean up empty ingredients and instructions
      const cleanedRecipe: Recipe = {
        ...recipe,
        ingredients: recipe.ingredients.filter(
          (ing) => (ing.display_text || ing.name).trim()
        ),
        instructions: recipe.instructions.filter((inst) => inst.trim()),
      };

      const result = await saveRecipe({
        sourceType: "manual",
        recipe: cleanedRecipe,
        parsingMethod: "manual",
        tags: tags.length > 0 ? tags : undefined,
        notes: notes.trim() || undefined,
      });

      if (imageFile) {
        await uploadRecipeThumbnail(result.user_recipe_id, imageFile);
      }

      navigate(`/recipes/${result.user_recipe_id}`);
    } catch (err) {
      const message =
        err instanceof RecipeError ? err.message : "Failed to save recipe";
      setError(message);
      setIsSaving(false);
    }
  };

  if (isSaving) {
    return (
      <div className="py-12">
        <LoadingSpinner message="Saving recipe..." />
      </div>
    );
  }

  // Show sign-in prompt for unauthenticated users in multi-tenant mode
  if (isAuthEnabled && !isAuthorized) {
    return (
      <div>
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-brown-dark mb-2">
            Add Recipe Manually
          </h2>
          <p className="text-brown-medium">
            Enter your recipe details below.
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
          <svg
            className="w-16 h-16 mx-auto text-gray-300 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
            />
          </svg>
          <h3 className="text-lg font-medium text-brown-dark mb-2">
            Sign in to add recipes
          </h3>
          <p className="text-brown-medium mb-4">
            Create an account or sign in to save recipes to your collection.
          </p>
          <p className="text-sm text-brown-medium">
            Want to try it out first?{" "}
            <a href="/add/url" className="text-coral hover:text-coral-dark">
              Extract a recipe from URL
            </a>{" "}
            without signing in.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-brown-dark mb-2">
          Add Recipe Manually
        </h2>
        <p className="text-brown-medium">
          Enter your recipe details below.
        </p>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorMessage message={error} />
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-4">
        <label className="block text-sm font-medium text-brown-medium mb-2">
          Recipe Photo
        </label>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          onChange={handleImageChange}
          className="hidden"
        />
        {imagePreviewUrl ? (
          <div className="relative inline-block">
            <img
              src={imagePreviewUrl}
              alt="Recipe preview"
              className="h-48 w-full object-cover rounded-lg"
            />
            <button
              type="button"
              onClick={handleRemoveImage}
              className="absolute top-2 right-2 p-1 bg-white rounded-full shadow text-gray-600 hover:text-red-600"
              aria-label="Remove image"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2 border border-dashed border-gray-300 rounded-lg text-sm text-brown-medium hover:border-coral hover:text-coral"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Add a photo
          </button>
        )}
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <RecipeEditor
          recipe={recipe}
          notes={notes}
          tags={tags}
          onRecipeChange={setRecipe}
          onNotesChange={setNotes}
          onTagsChange={setTags}
          onSave={handleSave}
          isSaving={isSaving}
          saveLabel="Save Recipe"
        />
      </div>
    </div>
  );
}
