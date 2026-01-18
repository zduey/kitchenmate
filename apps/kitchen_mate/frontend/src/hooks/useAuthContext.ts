import { useContext } from "react";
import { AuthContext } from "../contexts/authContextDef";

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuthContext must be used within AuthProvider");
  }
  return context;
}
