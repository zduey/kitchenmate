import { Recipe } from "../types/recipe";
import { ExportDropdown } from "./ExportDropdown";

interface RecipeCardProps {
  recipe: Recipe;
}

export function RecipeCard({ recipe }: RecipeCardProps) {
  const formatTime = (minutes: number): string => {
    if (minutes < 60) {
      return `${minutes} min`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

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
        <h2 className="text-2xl font-bold text-gray-900 mb-2">{recipe.title}</h2>

        {recipe.source_url && (
          <div className="mb-4">
            <a
              href={recipe.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 hover:underline"
              title={recipe.source_url}
            >
              <span className="truncate max-w-md">{recipe.source_url}</span>
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

        {recipe.metadata && (
          <div className="flex flex-wrap gap-4 mb-6 text-sm text-gray-600">
            {recipe.metadata.author && (
              <span className="flex items-center">
                <svg
                  className="h-4 w-4 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                  />
                </svg>
                {recipe.metadata.author}
              </span>
            )}
            {recipe.metadata.servings && (
              <span className="flex items-center">
                <svg
                  className="h-4 w-4 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                {recipe.metadata.servings}
              </span>
            )}
            {recipe.metadata.prep_time && (
              <span className="flex items-center">
                <svg
                  className="h-4 w-4 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Prep: {formatTime(recipe.metadata.prep_time)}
              </span>
            )}
            {recipe.metadata.cook_time && (
              <span className="flex items-center">
                <svg
                  className="h-4 w-4 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"
                  />
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

        {recipe.metadata?.categories && recipe.metadata.categories.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {recipe.metadata.categories.map((category, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full"
              >
                {category}
              </span>
            ))}
          </div>
        )}

        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Ingredients
          </h3>
          <ul className="space-y-2">
            {recipe.ingredients.map((ingredient, index) => (
              <li key={index} className="flex items-start">
                <span className="text-blue-600 mr-2">•</span>
                <span>{ingredient.display_text || ingredient.name}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Instructions
          </h3>
          <ol className="space-y-3">
            {recipe.instructions.map((instruction, index) => (
              <li key={index} className="flex">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white text-sm rounded-full flex items-center justify-center mr-3 mt-0.5">
                  {index + 1}
                </span>
                <span className="text-gray-700">{instruction}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="flex justify-end pt-4 border-t border-gray-200">
          <ExportDropdown recipe={recipe} />
        </div>
      </div>
    </div>
  );
}
