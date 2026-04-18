import type { Recipe } from "./recipe";

export interface CreateShareResponse {
  share_token: string;
  share_url: string;
  created_at: string;
  expires_at: string | null;
}

export interface SharedRecipeResponse {
  title: string;
  recipe: Recipe;
  shared_at: string;
}

export interface SaveSharedRecipeResponse {
  user_recipe_id: string;
  is_new: boolean;
}
