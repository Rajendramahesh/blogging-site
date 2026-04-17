"use client";
import { useState, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UnsplashPhoto {
  id: string;
  urls: { regular: string; small: string };
  alt_description: string | null;
  user: { name: string; links: { html: string } };
  links: { download_location: string };
}

interface Props {
  onSelect: (photo: UnsplashPhoto) => void;
  onClose: () => void;
}

export default function UnsplashModal({ onSelect, onClose }: Props) {
  const [query, setQuery] = useState("");
  const [photos, setPhotos] = useState<UnsplashPhoto[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const search = async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(
        `${API_URL}/unsplash/search?query=${encodeURIComponent(q)}&per_page=20`
      );
      if (!res.ok) throw new Error("Search failed");
      const data = await res.json();
      setPhotos(data.results ?? []);
      if ((data.results ?? []).length === 0) setError("No photos found.");
    } catch {
      setError("Could not load photos. Is Unsplash configured?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            {/* Unsplash wordmark icon */}
            <svg
              width="20"
              height="20"
              viewBox="0 0 32 32"
              fill="currentColor"
              className="text-gray-800"
            >
              <path d="M10 9V0h12v9H10zm12 5h10v18H0V14h10v9h12v-9z" />
            </svg>
            <span className="font-semibold text-gray-900">Search Unsplash</span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-xl leading-none"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Search bar */}
        <div className="flex gap-2 px-5 py-3 border-b border-gray-100">
          <input
            ref={inputRef}
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="Search free high-res photos…"
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
          />
          <button
            onClick={search}
            disabled={loading}
            className="px-4 py-2 bg-gray-900 text-white text-sm rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "…" : "Search"}
          </button>
        </div>

        {/* Results */}
        <div className="overflow-y-auto p-4 flex-1">
          {error && (
            <p className="text-center text-sm text-gray-500 mt-6">{error}</p>
          )}
          {!error && photos.length === 0 && !loading && (
            <p className="text-center text-sm text-gray-400 mt-6">
              Type something above to search photos
            </p>
          )}
          <div className="grid grid-cols-3 gap-2">
            {photos.map((photo) => (
              <button
                key={photo.id}
                onClick={() => onSelect(photo)}
                className="group relative aspect-video overflow-hidden rounded-lg bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-900"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={photo.urls.small}
                  alt={photo.alt_description ?? "Unsplash photo"}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                  loading="lazy"
                />
                {/* Attribution overlay on hover */}
                <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/60 to-transparent px-2 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <p className="text-white text-xs truncate">
                    {photo.user.name}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Footer attribution */}
        {photos.length > 0 && (
          <div className="px-5 py-2 border-t border-gray-100 text-xs text-gray-400 text-right">
            Photos by{" "}
            <a
              href="https://unsplash.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-gray-600"
            >
              Unsplash
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
