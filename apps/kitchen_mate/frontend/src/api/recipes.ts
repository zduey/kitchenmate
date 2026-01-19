import {
  ApiError,
  ListUserRecipesResponse,
  SaveRecipeRequest,
  SaveRecipeResponse,
  UpdateUserRecipeRequest,
  UserRecipe,
} from "../types/recipe";

const API_BASE = "/api";

export class RecipeError extends Error {
  constructor(
    message: string,
    public statusCode: number
  ) {
    super(message);
    this.name = "RecipeError";
  }
}

export interface ListRecipesParams {
  cursor?: string;
  limit?: number;
  tags?: string[];
  modifiedOnly?: boolean;
}

/**
 * List user's saved recipes with pagination and filtering.
 */
export async function listUserRecipes(
  params: ListRecipesParams = {}
): Promise<ListUserRecipesResponse> {
  const searchParams = new URLSearchParams();

  if (params.cursor) {
    searchParams.set("cursor", params.cursor);
  }
  if (params.limit) {
    searchParams.set("limit", params.limit.toString());
  }
  if (params.tags && params.tags.length > 0) {
    searchParams.set("tags", params.tags.join(","));
  }
  if (params.modifiedOnly) {
    searchParams.set("modified_only", "true");
  }

  const queryString = searchParams.toString();
  const url = `${API_BASE}/me/recipes${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new RecipeError(error.detail, response.status);
  }

  return response.json();
}

/**
 * Get a specific recipe from user's collection.
 */
export async function getUserRecipe(recipeId: string): Promise<UserRecipe> {
  const response = await fetch(`${API_BASE}/me/recipes/${recipeId}`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new RecipeError(error.detail, response.status);
  }

  return response.json();
}

/**
 * Save a recipe from URL to user's collection.
 */
export async function saveRecipe(
  url: string,
  options: { tags?: string[]; notes?: string } = {}
): Promise<SaveRecipeResponse> {
  const request: SaveRecipeRequest = {
    url,
    use_llm_fallback: true,
    tags: options.tags,
    notes: options.notes,
  };

  const response = await fetch(`${API_BASE}/me/recipes`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    credentials: "include",
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new RecipeError(error.detail, response.status);
  }

  return response.json();
}

/**
 * Update a recipe in user's collection.
 */
export async function updateUserRecipe(
  recipeId: string,
  updates: UpdateUserRecipeRequest
): Promise<{ id: string; is_modified: boolean; updated_at: string }> {
  const response = await fetch(`${API_BASE}/me/recipes/${recipeId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(updates),
    credentials: "include",
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new RecipeError(error.detail, response.status);
  }

  return response.json();
}

/**
 * Delete a recipe from user's collection.
 */
export async function deleteUserRecipe(recipeId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/me/recipes/${recipeId}`, {
    method: "DELETE",
    credentials: "include",
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new RecipeError(error.detail, response.status);
  }
}
