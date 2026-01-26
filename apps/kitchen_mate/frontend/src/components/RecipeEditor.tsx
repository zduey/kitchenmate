import { useState, KeyboardEvent } from "react";
import { Recipe, Ingredient, RecipeMetadata } from "../types/recipe";

interface RecipeEditorProps {
  recipe: Recipe;
  notes: string;
  tags: string[];
  onRecipeChange: (recipe: Recipe) => void;
  onNotesChange: (notes: string) => void;
  onTagsChange: (tags: string[]) => void;
  onSave: () => void;
  onCancel?: () => void;
  isSaving: boolean;
  saveLabel?: string;
}

export function RecipeEditor({
  recipe,
  notes,
  tags,
  onRecipeChange,
  onNotesChange,
  onTagsChange,
  onSave,
  onCancel,
  isSaving,
  saveLabel = "Save",
}: RecipeEditorProps) {
  const [newTag, setNewTag] = useState("");

  const updateTitle = (title: string) => {
    onRecipeChange({ ...recipe, title });
  };

  const updateMetadata = (field: keyof RecipeMetadata, value: string | number | undefined) => {
    const currentMetadata = recipe.metadata || {};
    const newMetadata = { ...currentMetadata, [field]: value };
    // Remove undefined values
    if (value === undefined || value === "") {
      delete newMetadata[field];
    }
    onRecipeChange({ ...recipe, metadata: Object.keys(newMetadata).length > 0 ? newMetadata : undefined });
  };

  const parseTimeValue = (value: string): number | undefined => {
    const num = parseInt(value, 10);
    return isNaN(num) || num < 0 ? undefined : num;
  };

  const updateIngredient = (index: number, field: keyof Ingredient, value: string) => {
    const newIngredients = [...recipe.ingredients];
    newIngredients[index] = { ...newIngredients[index], [field]: value };
    onRecipeChange({ ...recipe, ingredients: newIngredients });
  };

  const addIngredient = () => {
    onRecipeChange({
      ...recipe,
      ingredients: [...recipe.ingredients, { name: "", display_text: "" }],
    });
  };

  const removeIngredient = (index: number) => {
    const newIngredients = recipe.ingredients.filter((_, i) => i !== index);
    onRecipeChange({ ...recipe, ingredients: newIngredients });
  };

  const updateInstruction = (index: number, value: string) => {
    const newInstructions = [...recipe.instructions];
    newInstructions[index] = value;
    onRecipeChange({ ...recipe, instructions: newInstructions });
  };

  const addInstruction = () => {
    onRecipeChange({
      ...recipe,
      instructions: [...recipe.instructions, ""],
    });
  };

  const removeInstruction = (index: number) => {
    const newInstructions = recipe.instructions.filter((_, i) => i !== index);
    onRecipeChange({ ...recipe, instructions: newInstructions });
  };

  const handleAddTag = () => {
    const tag = newTag.trim().toLowerCase();
    if (tag && !tags.includes(tag)) {
      onTagsChange([...tags, tag]);
    }
    setNewTag("");
  };

  const handleRemoveTag = (tagToRemove: string) => {
    onTagsChange(tags.filter((t) => t !== tagToRemove));
  };

  const handleTagKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddTag();
    }
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <label className="block text-sm font-medium text-brown-medium mb-2">
          Recipe Title *
        </label>
        <input
          type="text"
          value={recipe.title}
          onChange={(e) => updateTitle(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-brown-dark focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
          placeholder="Enter recipe title"
        />
      </div>

      {/* Author */}
      <div>
        <label className="block text-sm font-medium text-brown-medium mb-2">
          Author
        </label>
        <input
          type="text"
          value={recipe.metadata?.author || ""}
          onChange={(e) => updateMetadata("author", e.target.value || undefined)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
          placeholder="Recipe author"
        />
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-brown-medium mb-2">
            Servings
          </label>
          <input
            type="text"
            value={recipe.metadata?.servings || ""}
            onChange={(e) => updateMetadata("servings", e.target.value || undefined)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
            placeholder="e.g., 4"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-brown-medium mb-2">
            Prep Time
          </label>
          <div className="relative">
            <input
              type="number"
              min="0"
              value={recipe.metadata?.prep_time ?? ""}
              onChange={(e) => updateMetadata("prep_time", parseTimeValue(e.target.value))}
              className="w-full px-3 py-2 pr-12 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
              placeholder="0"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-brown-medium">min</span>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-brown-medium mb-2">
            Cook Time
          </label>
          <div className="relative">
            <input
              type="number"
              min="0"
              value={recipe.metadata?.cook_time ?? ""}
              onChange={(e) => updateMetadata("cook_time", parseTimeValue(e.target.value))}
              className="w-full px-3 py-2 pr-12 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
              placeholder="0"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-brown-medium">min</span>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-brown-medium mb-2">
            Total Time
          </label>
          <div className="relative">
            <input
              type="number"
              min="0"
              value={recipe.metadata?.total_time ?? ""}
              onChange={(e) => updateMetadata("total_time", parseTimeValue(e.target.value))}
              className="w-full px-3 py-2 pr-12 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
              placeholder="0"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-brown-medium">min</span>
          </div>
        </div>
      </div>

      {/* Ingredients */}
      <div>
        <label className="block text-sm font-medium text-brown-medium mb-2">
          Ingredients *
        </label>
        <div className="space-y-2">
          {recipe.ingredients.map((ingredient, index) => (
            <div key={index} className="flex gap-2 items-start">
              <input
                type="text"
                value={ingredient.display_text || ingredient.name}
                onChange={(e) => updateIngredient(index, "display_text", e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
                placeholder="e.g., 1 cup flour"
              />
              <button
                type="button"
                onClick={() => removeIngredient(index)}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                aria-label="Remove ingredient"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addIngredient}
            className="text-sm text-coral hover:text-coral-dark"
          >
            + Add Ingredient
          </button>
        </div>
      </div>

      {/* Instructions */}
      <div>
        <label className="block text-sm font-medium text-brown-medium mb-2">
          Instructions *
        </label>
        <div className="space-y-3">
          {recipe.instructions.map((instruction, index) => (
            <div key={index} className="flex gap-2 items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-coral text-white text-sm rounded-full flex items-center justify-center mt-2">
                {index + 1}
              </span>
              <textarea
                value={instruction}
                onChange={(e) => updateInstruction(index, e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
                rows={2}
                placeholder="Enter instruction step"
              />
              <button
                type="button"
                onClick={() => removeInstruction(index)}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                aria-label="Remove step"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addInstruction}
            className="text-sm text-coral hover:text-coral-dark"
          >
            + Add Step
          </button>
        </div>
      </div>

      {/* Tags */}
      <div>
        <label className="block text-sm font-medium text-brown-medium mb-2">
          Tags
        </label>
        <div className="flex flex-wrap gap-2 mb-2">
          {tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center px-2 py-1 bg-coral bg-opacity-10 text-coral-dark text-sm rounded-full"
            >
              {tag}
              <button
                type="button"
                onClick={() => handleRemoveTag(tag)}
                className="ml-1 text-coral hover:text-coral-dark"
                aria-label={`Remove tag ${tag}`}
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyPress={handleTagKeyPress}
            placeholder="Add a tag"
            className="flex-1 px-3 py-1 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
          />
          <button
            type="button"
            onClick={handleAddTag}
            className="px-3 py-1 bg-gray-100 text-brown-medium rounded-lg hover:bg-gray-200 text-sm"
          >
            Add
          </button>
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="block text-sm font-medium text-brown-medium mb-2">
          Personal Notes
        </label>
        <textarea
          value={notes}
          onChange={(e) => onNotesChange(e.target.value)}
          placeholder="Add your notes about this recipe..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
          rows={3}
        />
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-brown-medium hover:bg-gray-100 rounded-lg"
            disabled={isSaving}
          >
            Cancel
          </button>
        )}
        <button
          type="button"
          onClick={onSave}
          disabled={isSaving || !recipe.title.trim()}
          className="px-4 py-2 bg-coral text-white rounded-lg hover:bg-coral-dark disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? "Saving..." : saveLabel}
        </button>
      </div>
    </div>
  );
}
