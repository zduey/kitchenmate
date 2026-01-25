export interface Ingredient {
  name: string;
  amount?: string;
  unit?: string;
  preparation?: string;
  display_text?: string;
}

export interface RecipeMetadata {
  author?: string;
  servings?: string;
  prep_time?: number;
  cook_time?: number;
  total_time?: number;
  categories?: string[];
}

export interface Recipe {
  title: string;
  ingredients: Ingredient[];
  instructions: string[];
  source_url?: string;
  image?: string;
  metadata?: RecipeMetadata;
}

export type OutputFormat = "json" | "text" | "markdown" | "pdf" | "jpeg" | "png" | "webp" | "svg";

export interface ClipRequest {
  url: string;
  timeout?: number;
  use_llm_fallback?: boolean;
  force_llm?: boolean;
  force_refresh?: boolean;
}

export interface ClipResponse {
  recipe: Recipe;
  cached: boolean;
  content_changed: boolean | null;
}

export interface FileInfo {
  filename: string;
  file_type: "image" | "document";
  file_size_bytes: number;
  content_type: string;
}

export interface ClipUploadResponse {
  recipe: Recipe;
  file_info: FileInfo;
  parsing_method: string;
}

export interface ConvertRequest {
  recipe: Recipe;
  format: Exclude<OutputFormat, "json">;
}

export interface ApiError {
  detail: string;
}

// =============================================================================
// User Recipe Types
// =============================================================================

export type SourceType = "web" | "upload" | "manual";

export interface SaveRecipeRequest {
  source_type?: SourceType;
  url?: string;
  recipe?: Recipe;
  parsing_method?: string;
  timeout?: number;
  use_llm_fallback?: boolean;
  tags?: string[];
  notes?: string;
}

export interface SaveRecipeResponse {
  user_recipe_id: string;
  recipe_id: string;
  source_url: string;
  parsing_method: string;
  created_at: string;
  is_new: boolean;
}

export interface UserRecipeSummary {
  id: string;
  source_url: string;
  title: string;
  image_url: string | null;
  is_modified: boolean;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ListUserRecipesResponse {
  recipes: UserRecipeSummary[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface RecipeLineage {
  recipe_id: string;
  parsed_at: string;
}

export interface UserRecipe {
  id: string;
  source_url: string;
  parsing_method: string;
  is_modified: boolean;
  notes: string | null;
  tags: string[] | null;
  recipe: Recipe;
  lineage: RecipeLineage;
  created_at: string;
  updated_at: string;
}

export interface UpdateUserRecipeRequest {
  recipe?: Recipe;
  notes?: string;
  tags?: string[];
}
