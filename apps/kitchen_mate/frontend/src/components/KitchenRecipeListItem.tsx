import { Link } from "react-router-dom";
import { formatTagForDisplay } from "../utils/tags";
import type { KitchenRecipe } from "../types/kitchen";

interface KitchenRecipeListItemProps {
  recipe: KitchenRecipe;
  kitchenId: string;
  kitchenName: string;
  onRemove?: () => void;
  removing?: boolean;
}

export function KitchenRecipeListItem({ recipe, kitchenId, kitchenName, onRemove, removing }: KitchenRecipeListItemProps) {
  const tags = recipe.tags ?? [];

  return (
    <div className="group block bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
      <Link to={`/kitchens/${kitchenId}/recipes/${recipe.id}`}>
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

          <span className="absolute bottom-2 left-2 px-2 py-0.5 bg-white/80 backdrop-blur-sm text-coral text-xs font-medium rounded-full">
            {kitchenName}
          </span>

          {onRemove && (
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onRemove();
              }}
              disabled={removing}
              className="absolute top-2 right-2 p-1 bg-black/40 hover:bg-red-600 text-white rounded-full transition-colors disabled:opacity-50"
              title="Remove from kitchen"
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </Link>

      <div className="p-4">
        <Link to={`/kitchens/${kitchenId}/recipes/${recipe.id}`}>
          <h3 className="font-semibold text-brown-dark group-hover:text-coral transition-colors line-clamp-2">
            {recipe.title}
          </h3>
        </Link>

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
        </div>

        <p className="mt-2 text-xs text-gray-500">
          {new Date(recipe.shared_at).toLocaleDateString()}
        </p>
      </div>
    </div>
  );
}
