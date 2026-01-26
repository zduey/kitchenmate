import { formatTagForDisplay } from "../utils/tags";

interface TagCounts {
  tags: Map<string, number>;
  untagged: number;
}

interface TagGroupsViewProps {
  tagCounts: TagCounts;
  onTagSelect: (tag: string) => void;
  hasMore: boolean;
  onLoadMore: () => void;
  loadingMore: boolean;
}

function TagIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
      />
    </svg>
  );
}

function TagCard({
  tag,
  count,
  onClick,
  isUntagged = false,
}: {
  tag: string;
  count: number;
  onClick: () => void;
  isUntagged?: boolean;
}) {
  const displayLabel = isUntagged ? "Untagged" : formatTagForDisplay(tag);

  return (
    <button
      onClick={onClick}
      className="p-4 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md hover:border-coral transition-all text-left w-full"
    >
      <div className="flex items-center gap-2 mb-2">
        <TagIcon className={`h-5 w-5 ${isUntagged ? "text-gray-400" : "text-coral"}`} />
        <span className="font-medium text-brown-dark truncate">{displayLabel}</span>
      </div>
      <p className="text-sm text-brown-medium">
        {count} {count === 1 ? "recipe" : "recipes"}
      </p>
    </button>
  );
}

export function TagGroupsView({
  tagCounts,
  onTagSelect,
  hasMore,
  onLoadMore,
  loadingMore,
}: TagGroupsViewProps) {
  const sortedTags = Array.from(tagCounts.tags.entries()).sort(
    (a, b) => b[1] - a[1]
  );

  const isEmpty = sortedTags.length === 0 && tagCounts.untagged === 0;

  if (isEmpty) {
    return (
      <div className="py-12 text-center">
        <div className="text-gray-400 mb-4">
          <TagIcon className="h-16 w-16 mx-auto" />
        </div>
        <h3 className="text-lg font-medium text-brown-dark mb-2">No tags yet</h3>
        <p className="text-brown-medium">
          Add tags to your recipes to organize them into groups.
        </p>
      </div>
    );
  }

  return (
    <div>
      {hasMore && (
        <div className="mb-4 p-3 bg-amber-50 text-amber-800 rounded-lg text-sm flex items-center justify-between">
          <span>Showing tags from loaded recipes.</span>
          <button
            onClick={onLoadMore}
            disabled={loadingMore}
            className="underline hover:no-underline disabled:opacity-50"
          >
            {loadingMore ? "Loading..." : "Load more to see all"}
          </button>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {tagCounts.untagged > 0 && (
          <TagCard
            tag="__untagged__"
            count={tagCounts.untagged}
            onClick={() => onTagSelect("__untagged__")}
            isUntagged
          />
        )}

        {sortedTags.map(([tag, count]) => (
          <TagCard
            key={tag}
            tag={tag}
            count={count}
            onClick={() => onTagSelect(tag)}
          />
        ))}
      </div>
    </div>
  );
}
