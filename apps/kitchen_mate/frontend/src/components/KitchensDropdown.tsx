import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { listKitchens, KitchenError } from "../api/kitchens";
import type { KitchenSummary } from "../types/kitchen";

export function KitchensDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const [kitchens, setKitchens] = useState<KitchenSummary[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listKitchens().catch((err) => {
      if (!(err instanceof KitchenError)) console.error(err);
    }).then((result) => {
      if (result) setKitchens(result);
    });
  }, []);

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
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 text-sm font-medium text-brown-medium hover:text-coral transition-colors"
      >
        Kitchens
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute left-0 mt-2 w-52 bg-white rounded-lg shadow-lg border border-gray-200 z-50 py-1">
          {kitchens.length > 0 ? (
            <>
              {kitchens.map((kitchen) => (
                <Link
                  key={kitchen.id}
                  to={`/kitchens/${kitchen.id}`}
                  onClick={() => setIsOpen(false)}
                  className="block px-4 py-2.5 text-sm text-brown-dark hover:bg-gray-50 hover:text-coral transition-colors"
                >
                  {kitchen.name}
                </Link>
              ))}
              <div className="border-t border-gray-100 mt-1 pt-1">
                <Link
                  to="/kitchens"
                  onClick={() => setIsOpen(false)}
                  className="block px-4 py-2 text-xs text-brown-medium hover:text-coral transition-colors"
                >
                  Manage Kitchens
                </Link>
              </div>
            </>
          ) : (
            <>
              <p className="px-4 py-2.5 text-sm text-brown-medium">No kitchens yet.</p>
              <div className="border-t border-gray-100 mt-1 pt-1">
                <Link
                  to="/kitchens"
                  onClick={() => setIsOpen(false)}
                  className="block px-4 py-2 text-xs text-brown-medium hover:text-coral transition-colors"
                >
                  Manage Kitchens
                </Link>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
