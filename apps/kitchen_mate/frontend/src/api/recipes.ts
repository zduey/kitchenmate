import {
  ApiError,
  ListUserRecipesResponse,
  Recipe,
  SaveRecipeRequest,
  SaveRecipeResponse,
  UpdateUserRecipeRequest,
  UserRecipe,
  getErrorMessage,
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
  search?: string;
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
  if (params.search) {
    searchParams.set("search", params.search);
  }

  const queryString = searchParams.toString();
  const url = `${API_BASE}/me/recipes${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    const message = getErrorMessage(error.detail, "Failed to list recipes");
    throw new RecipeError(message, response.status);
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
    const message = getErrorMessage(error.detail, "Failed to get recipe");
    throw new RecipeError(message, response.status);
  }

  return response.json();
}

export type SaveRecipeParams =
  | { url: string; tags?: string[]; notes?: string }
  | { sourceType: "upload"; recipe: Recipe; parsingMethod: string; tags?: string[]; notes?: string }
  | { sourceType: "manual"; recipe: Recipe; parsingMethod: "manual"; tags?: string[]; notes?: string };

/**
 * Save a recipe to user's collection.
 * Supports both URL-based and upload-based saving.
 */
export async function saveRecipe(params: SaveRecipeParams): Promise<SaveRecipeResponse> {
  let request: SaveRecipeRequest;

  if ("url" in params) {
    // URL-based save
    request = {
      source_type: "web",
      url: params.url,
      use_llm_fallback: true,
      tags: params.tags,
      notes: params.notes,
    };
  } else {
    // Upload or manual save
    request = {
      source_type: params.sourceType,
      recipe: params.recipe,
      parsing_method: params.parsingMethod,
      tags: params.tags,
      notes: params.notes,
    };
  }

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
    const message = getErrorMessage(error.detail, "Failed to save recipe");
    throw new RecipeError(message, response.status);
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
    const message = getErrorMessage(error.detail, "Failed to update recipe");
    throw new RecipeError(message, response.status);
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
    const message = getErrorMessage(error.detail, "Failed to delete recipe");
    throw new RecipeError(message, response.status);
  }
}
