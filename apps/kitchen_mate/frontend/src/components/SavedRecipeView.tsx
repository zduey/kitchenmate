import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Recipe, UserRecipe } from "../types/recipe";
import {
  getUserRecipe,
  updateUserRecipe,
  deleteUserRecipe,
  RecipeError,
} from "../api/recipes";
import { RecipeEditor } from "./RecipeEditor";
import { ExportDropdown } from "./ExportDropdown";
import { LoadingSpinner } from "./LoadingSpinner";
import { formatTagForDisplay, normalizeTag } from "../utils/tags";

export function SavedRecipeView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [userRecipe, setUserRecipe] = useState<UserRecipe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Edit state
  const [editedRecipe, setEditedRecipe] = useState<Recipe | null>(null);
  const [editedNotes, setEditedNotes] = useState("");
  const [editedTags, setEditedTags] = useState<string[]>([]);

  useEffect(() => {
    if (!id) return;

    setLoading(true);
    getUserRecipe(id)
      .then((data) => {
        setUserRecipe(data);
        setEditedRecipe(data.recipe);
        setEditedNotes(data.notes || "");
        setEditedTags(data.tags || []);
      })
      .catch((err) => {
        const message =
          err instanceof RecipeError ? err.message : "Failed to load recipe";
        setError(message);
      })
      .finally(() => setLoading(false));
  }, [id]);

  const handleSave = async () => {
    if (!id || !editedRecipe) return;

    setIsSaving(true);
    try {
      await updateUserRecipe(id, {
        recipe: editedRecipe,
        notes: editedNotes || undefined,
        tags: editedTags.length > 0 ? editedTags : undefined,
      });
      // Refresh data
      const updated = await getUserRecipe(id);
      setUserRecipe(updated);
      setIsEditing(false);
    } catch (err) {
      const message =
        err instanceof RecipeError ? err.message : "Failed to save changes";
      setError(message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;

    setIsDeleting(true);
    try {
      await deleteUserRecipe(id);
      navigate("/");
    } catch (err) {
      const message =
        err instanceof RecipeError ? err.message : "Failed to delete recipe";
      setError(message);
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const handleCancelEdit = () => {
    if (userRecipe) {
      setEditedRecipe(userRecipe.recipe);
      setEditedNotes(userRecipe.notes || "");
      setEditedTags(userRecipe.tags || []);
    }
    setIsEditing(false);
  };

  const formatTime = (minutes: number): string => {
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
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
        <Link
          to="/"
          className="text-coral hover:text-coral-dark"
        >
          Back to recipes
        </Link>
      </div>
    );
  }

  if (!userRecipe || !editedRecipe) {
    return (
      <div className="py-12 text-center">
        <p className="text-brown-medium mb-4">Recipe not found</p>
        <Link
          to="/"
          className="text-coral hover:text-coral-dark"
        >
          Back to recipes
        </Link>
      </div>
    );
  }

  const recipe = userRecipe.recipe;

  // Edit mode - use RecipeEditor
  if (isEditing) {
    return (
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {recipe.image && (
          <img
            src={recipe.image}
            alt={recipe.title}
            className="w-full h-64 object-cover"
          />
        )}
        <div className="p-6">
          <RecipeEditor
            recipe={editedRecipe}
            notes={editedNotes}
            tags={editedTags}
            onRecipeChange={setEditedRecipe}
            onNotesChange={setEditedNotes}
            onTagsChange={setEditedTags}
            onSave={handleSave}
            onCancel={handleCancelEdit}
            isSaving={isSaving}
            saveLabel="Save Changes"
          />
        </div>
      </div>
    );
  }

  // View mode
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      {/* Image */}
      {recipe.image && (
        <img
          src={recipe.image}
          alt={recipe.title}
          className="w-full h-64 object-cover"
        />
      )}

      <div className="p-6">
        {/* Header with title and actions */}
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-brown-dark">{recipe.title}</h2>

            {userRecipe.is_modified && (
              <span className="inline-block mt-2 px-2 py-1 bg-coral bg-opacity-10 text-coral-dark text-xs rounded">
                Modified from original
              </span>
            )}
          </div>

          <div className="flex gap-2 ml-4">
            <button
              onClick={() => setIsEditing(true)}
              className="p-2 text-brown-medium hover:text-coral hover:bg-coral hover:bg-opacity-10 rounded"
              title="Edit recipe"
            >
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="p-2 text-brown-medium hover:text-red-600 hover:bg-red-50 rounded"
              title="Delete recipe"
            >
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Source URL */}
        {userRecipe.source_url && !userRecipe.source_url.startsWith("upload://") && !userRecipe.source_url.startsWith("manual://") && (
          <div className="mb-4">
            <a
              href={userRecipe.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-sm text-coral hover:text-coral-dark hover:underline"
            >
              <span className="truncate max-w-md">{userRecipe.source_url}</span>
              <svg
                className="ml-1 h-4 w-4 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
            </a>
          </div>
        )}

        {/* Metadata */}
        {recipe.metadata && (
          <div className="flex flex-wrap gap-4 mb-6 text-sm text-brown-medium">
            {recipe.metadata.author && (
              <span className="flex items-center">
                <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                {recipe.metadata.author}
              </span>
            )}
            {recipe.metadata.servings && (
              <span className="flex items-center">
                <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {recipe.metadata.servings}
              </span>
            )}
            {recipe.metadata.prep_time && (
              <span className="flex items-center">
                <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Prep: {formatTime(recipe.metadata.prep_time)}
              </span>
            )}
            {recipe.metadata.cook_time && (
              <span className="flex items-center">
                <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
                </svg>
                Cook: {formatTime(recipe.metadata.cook_time)}
              </span>
            )}
            {recipe.metadata.total_time && (
              <span className="flex items-center font-medium">
                Total: {formatTime(recipe.metadata.total_time)}
              </span>
            )}
          </div>
        )}

        {/* Tags */}
        {userRecipe.tags && userRecipe.tags.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-brown-medium mb-2">Tags</h3>
            <div className="flex flex-wrap gap-2">
              {userRecipe.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-1 bg-gray-100 text-brown-medium text-sm rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Notes */}
        {userRecipe.notes && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-brown-medium mb-2">Personal Notes</h3>
            <p className="text-brown-medium text-sm">{userRecipe.notes}</p>
          </div>
        )}

        {/* Ingredients */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-brown-dark mb-3">Ingredients</h3>
          <ul className="space-y-2">
            {recipe.ingredients.map((ingredient, index) => (
              <li key={index} className="flex items-start">
                <span className="text-coral mr-2">•</span>
                <span>{ingredient.display_text || ingredient.name}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Instructions */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-brown-dark mb-3">Instructions</h3>
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

        {/* Footer */}
        <div className="flex justify-between items-center pt-4 border-t border-gray-200">
          <Link
            to="/"
            className="text-coral hover:text-coral-dark flex items-center"
          >
            <svg className="h-5 w-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to recipes
          </Link>
          <ExportDropdown recipe={recipe} />
        </div>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm mx-4">
            <h3 className="text-lg font-semibold text-brown-dark mb-2">
              Delete Recipe?
            </h3>
            <p className="text-brown-medium mb-4">
              Are you sure you want to remove this recipe from your collection? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
                className="px-4 py-2 text-brown-medium hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {isDeleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
