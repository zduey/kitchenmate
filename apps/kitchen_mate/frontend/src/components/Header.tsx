import { Link } from "react-router-dom";
import { useAuthContext } from "../hooks/useAuthContext";
import { UserDropdown } from "./UserDropdown";

interface HeaderProps {
  onSignInClick: () => void;
}

export function Header({ onSignInClick }: HeaderProps) {
  const { user, signOut, loading, isAuthEnabled } = useAuthContext();

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (err) {
      console.error("Sign out error:", err);
    }
  };

  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-5xl mx-auto px-4 py-4 flex justify-between items-center">
        <Link to="/" className="hover:opacity-80 transition-opacity">
          <h1 className="text-2xl font-bold text-gray-900">Kitchen Mate</h1>
          <p className="text-sm text-gray-600">
            Your recipe collection
          </p>
        </Link>

        <div className="flex items-center gap-4">
          {isAuthEnabled && !loading && (
            <>
              {user ? (
                <UserDropdown user={user} onSignOut={handleSignOut} />
              ) : (
                <button
                  onClick={onSignInClick}
                  title="Save recipes, build collections, and more"
                  className="px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  Sign In
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </header>
  );
}
