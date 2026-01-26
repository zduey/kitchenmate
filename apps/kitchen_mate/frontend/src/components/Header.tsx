import { Link } from "react-router-dom";
import { useAuthContext } from "../hooks/useAuthContext";
import { useRequireAuth } from "../hooks/useRequireAuth";
import { UserDropdown } from "./UserDropdown";
import { AddRecipeDropdown } from "./AddRecipeDropdown";

interface HeaderProps {
  onSignInClick: () => void;
}

function BookmarkIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 100 125"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="bookmarkGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#e85d3d" />
          <stop offset="100%" stopColor="#d64a2f" />
        </linearGradient>
      </defs>
      <path
        d="M 0 0 L 100 0 L 100 106.25 L 50 87.5 L 0 106.25 Z"
        fill="url(#bookmarkGradient)"
      />
    </svg>
  );
}

export function Header({ onSignInClick }: HeaderProps) {
  const { user, signOut, loading, isAuthEnabled } = useAuthContext();
  const { isAuthorized } = useRequireAuth();

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
        <div className="flex items-center gap-8">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <BookmarkIcon className="w-5 h-6" />
            <span className="font-serif text-2xl text-brown-dark tracking-tight">
              <span className="font-light">Reci</span>
              <span className="font-semibold">pleased</span>
            </span>
          </Link>

          {/* Navigation */}
          <nav className="flex items-center gap-6">
            {isAuthorized ? (
              <Link
                to="/"
                className="text-sm font-medium text-brown-medium hover:text-coral transition-colors"
              >
                My Recipes
              </Link>
            ) : (
              <span
                className="text-sm font-medium text-gray-400 cursor-not-allowed"
                title="Sign in to access your recipes"
              >
                My Recipes
              </span>
            )}

            <AddRecipeDropdown variant="button" />
          </nav>
        </div>

        {/* Auth */}
        <div className="flex items-center gap-4">
          {isAuthEnabled && !loading && (
            <>
              {user ? (
                <UserDropdown user={user} onSignOut={handleSignOut} />
              ) : (
                <button
                  onClick={onSignInClick}
                  title="Save recipes, build collections, and more"
                  className="px-4 py-2 text-sm text-coral hover:bg-coral hover:bg-opacity-10 rounded-lg transition-colors"
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
