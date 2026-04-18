export interface KitchenMember {
  user_id: string;
  email: string | null;
  role: string;
  joined_at: string;
}

export interface KitchenSummary {
  id: string;
  name: string;
  created_by: string;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface KitchenDetail {
  id: string;
  name: string;
  created_by: string;
  members: KitchenMember[];
  created_at: string;
  updated_at: string;
}

export interface KitchenRecipe {
  id: string;
  kitchen_id: string;
  user_recipe_id: string;
  shared_by: string;
  shared_at: string;
  title: string;
  image_url: string | null;
  tags: string[] | null;
}

export interface ListKitchenRecipesResponse {
  recipes: KitchenRecipe[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface AddMemberResponse {
  added: boolean;
  message: string;
}
