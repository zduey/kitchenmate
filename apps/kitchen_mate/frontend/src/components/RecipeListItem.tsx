import { useState, KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import { UserRecipeSummary } from "../types/recipe";
import { updateUserRecipe } from "../api/recipes";
import { formatTagForDisplay, normalizeTag } from "../utils/tags";

interface RecipeListItemProps {
  recipe: UserRecipeSummary;
  onTagsUpdated?: (recipeId: string, tags: string[]) => void;
}

export function RecipeListItem({ recipe, onTagsUpdated }: RecipeListItemProps) {
  const [isAddingTag, setIsAddingTag] = useState(false);
  const [newTag, setNewTag] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localTags, setLocalTags] = useState<string[] | null>(recipe.tags);

  const tags = localTags ?? [];

  const handleAddTag = async () => {
    const tag = normalizeTag(newTag);
    if (!tag || tags.includes(tag)) {
      setNewTag("");
      setIsAddingTag(false);
      return;
    }

    setIsSubmitting(true);
    try {
      const updatedTags = [...tags, tag];
      await updateUserRecipe(recipe.id, { tags: updatedTags });
      setLocalTags(updatedTags);
      onTagsUpdated?.(recipe.id, updatedTags);
      setNewTag("");
      setIsAddingTag(false);
    } catch (err) {
      console.error("Failed to add tag:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddTag();
    } else if (e.key === "Escape") {
      setNewTag("");
      setIsAddingTag(false);
    }
  };

  const handleTagClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsAddingTag(true);
  };

  return (
    <div className="group block bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
      {/* Image - Links to detail */}
      <Link to={`/recipes/${recipe.id}`}>
        <div className="aspect-[4/3] bg-gray-100 relative overflow-hidden">
          {recipe.image_url ? (
            <img
              src={recipe.image_url}
              alt={recipe.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400">
              <svg className="h-16 w-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            </div>
          )}

          {/* Modified badge */}
          {recipe.is_modified && (
            <span className="absolute top-2 right-2 px-2 py-1 bg-coral text-white text-xs font-medium rounded">
              Modified
            </span>
          )}
        </div>
      </Link>

      {/* Content */}
      <div className="p-4">
        <Link to={`/recipes/${recipe.id}`}>
          <h3 className="font-semibold text-brown-dark group-hover:text-coral transition-colors line-clamp-2">
            {recipe.title}
          </h3>
        </Link>

        {/* Tags */}
        <div className="mt-2 flex flex-wrap gap-1 items-center min-h-[26px]">
          {tags.slice(0, 3).map((tag, index) => (
            <span
              key={index}
              className="px-2 py-0.5 bg-gray-100 text-brown-medium text-xs rounded-full"
            >
              {formatTagForDisplay(tag)}
            </span>
          ))}
          {tags.length > 3 && (
            <span className="text-xs text-gray-500">+{tags.length - 3}</span>
          )}

          {/* Add tag button/input */}
          {isAddingTag ? (
            <input
              type="text"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onKeyDown={handleKeyPress}
              onBlur={() => {
                if (!newTag.trim()) {
                  setIsAddingTag(false);
                }
              }}
              placeholder="Tag..."
              disabled={isSubmitting}
              autoFocus
              className="px-2 py-0.5 text-xs border border-gray-300 rounded-full w-20 focus:outline-none focus:ring-1 focus:ring-coral focus:border-coral"
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <button
              onClick={handleTagClick}
              className="px-2 py-0.5 text-xs text-gray-400 hover:text-coral hover:bg-gray-100 rounded-full transition-colors"
              title="Add tag"
            >
              + tag
            </button>
          )}
        </div>

        {/* Date */}
        <p className="mt-2 text-xs text-gray-500">
          {new Date(recipe.created_at).toLocaleDateString()}
        </p>
      </div>
    </div>
  );
}
