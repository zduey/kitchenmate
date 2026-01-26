import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Recipe } from "../types/recipe";
import { saveRecipe, RecipeError } from "../api/recipes";
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
  const navigate = useNavigate();
  const { isAuthorized } = useRequireAuth();
  const { isAuthEnabled } = useAuthContext();

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
