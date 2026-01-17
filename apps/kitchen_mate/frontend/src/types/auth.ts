export interface User {
  id: string;
  email: string | null;
}

export interface AuthState {
  user: User | null;
  loading: boolean;
}
