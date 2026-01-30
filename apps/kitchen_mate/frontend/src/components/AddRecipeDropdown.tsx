import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { useRequireAuth } from "../hooks/useRequireAuth";

interface AddRecipeDropdownProps {
  variant?: "button" | "plus";
}

const menuItems = [
  { label: "From URL", path: "/add/url", description: "Extract from a webpage", requiresAuth: false, requiresPro: false },
  { label: "Upload File", path: "/add/upload", description: "From image or document", requiresAuth: true, requiresPro: true },
  { label: "Enter Manually", path: "/add/manual", description: "Type it yourself", requiresAuth: true, requiresPro: false },
];

export function AddRecipeDropdown({ variant = "button" }: AddRecipeDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { isAuthorized, isPro } = useRequireAuth();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      {variant === "button" ? (
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-1 text-sm font-medium text-brown-medium hover:text-coral transition-colors"
        >
          Add Recipe
          <svg
            className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      ) : (
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center justify-center w-10 h-10 bg-coral text-white rounded-full hover:bg-coral-dark shadow-lg transition-colors"
          aria-label="Add recipe"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>
      )}

      {isOpen && (
        <div
          className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 z-50 py-1"
        >
          {menuItems.map((item, index) => {
            const needsAuth = item.requiresAuth && !isAuthorized;
            const needsUpgrade = item.requiresPro && !isPro;
            const isDisabled = needsAuth || needsUpgrade;
            const borderClass = index !== menuItems.length - 1 ? "border-b border-gray-100" : "";

            if (isDisabled) {
              const title = needsUpgrade
                ? "Pro feature - upgrade to unlock"
                : "Sign in to use this feature";

              return (
                <div
                  key={item.path}
                  className={`block px-4 py-3 cursor-not-allowed ${borderClass}`}
                  title={title}
                >
                  <span className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-400">{item.label}</span>
                    {needsUpgrade && (
                      <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-medium">
                        Pro
                      </span>
                    )}
                  </span>
                  <span className="block text-xs text-gray-400">{item.description}</span>
                </div>
              );
            }

            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsOpen(false)}
                className={`block px-4 py-3 hover:bg-gray-50 ${borderClass}`}
              >
                <span className="block text-sm font-medium text-brown-dark">{item.label}</span>
                <span className="block text-xs text-brown-medium">{item.description}</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
