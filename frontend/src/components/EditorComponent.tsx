"use client";
import { useEffect, useRef, useState } from "react";
import type { OutputData } from "@editorjs/editorjs";
import { getAccessToken } from "@/lib/api";
import UnsplashModal, { type UnsplashPhoto } from "./UnsplashModal";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Props {
  data?: OutputData;
  onChange: (data: OutputData) => void;
  placeholder?: string;
}

export default function EditorComponent({ data, onChange, placeholder }: Props) {
  const editorRef = useRef<unknown>(null);
  const holderRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);
  const [showUnsplash, setShowUnsplash] = useState(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const initEditor = async () => {
      const EditorJS = (await import("@editorjs/editorjs")).default;
      const Header = (await import("@editorjs/header")).default;
      const List = (await import("@editorjs/list")).default;
      const Quote = (await import("@editorjs/quote")).default;
      const ImageTool = (await import("@editorjs/image")).default;

      const editor = new EditorJS({
        holder: holderRef.current!,
        data: data || undefined,
        placeholder: placeholder || "Tell your story...",
        tools: {
          header: {
            // @ts-ignore
            class: Header,
            config: { levels: [2, 3, 4], defaultLevel: 2 },
          },
          // @ts-ignore
          list: { class: List, inlineToolbar: true },
          // @ts-ignore
          quote: { class: Quote, inlineToolbar: true },
          image: {
            // @ts-ignore
            class: ImageTool,
            config: {
              uploader: {
                uploadByFile: async (file: File) => {
                  const formData = new FormData();
                  formData.append("image", file);
                  const token = getAccessToken();
                  const res = await fetch(`${API_URL}/upload/image`, {
                    method: "POST",
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                    body: formData,
                    credentials: "include",
                  });
                  return res.json();
                },
                uploadByUrl: async (url: string) => {
                  const token = getAccessToken();
                  const res = await fetch(`${API_URL}/upload/by-url`, {
                    method: "POST",
                    headers: {
                      "Content-Type": "application/json",
                      ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    },
                    body: JSON.stringify({ url }),
                    credentials: "include",
                  });
                  return res.json();
                },
              },
            },
          },
        },
        onChange: async () => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const saved = await (editor as any).save();
          onChange(saved);
        },
      });
      editorRef.current = editor;
    };

    initEditor();

    return () => {
      if (editorRef.current) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (editorRef.current as any).destroy?.();
        editorRef.current = null;
        initialized.current = false;
      }
    };
  }, []);

  const handleUnsplashSelect = async (photo: UnsplashPhoto) => {
    setShowUnsplash(false);
    if (!editorRef.current) return;

    // Notify Unsplash of the download (required by their API guidelines)
    fetch(`${API_URL}/unsplash/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ download_location: photo.links.download_location }),
      credentials: "include",
    }).catch(() => {});

    // Insert image block using the regular Unsplash CDN URL
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (editorRef.current as any).blocks.insert("image", {
      file: { url: photo.urls.regular },
      caption: photo.alt_description ?? "",
      withBorder: false,
      withBackground: false,
      stretched: false,
    });
  };

  return (
    <div className="relative">
      {/* Unsplash trigger button */}
      <div className="flex justify-end mb-2">
        <button
          type="button"
          onClick={() => setShowUnsplash(true)}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 px-3 py-1.5 rounded-md hover:bg-gray-100 transition-colors"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 32 32"
            fill="currentColor"
          >
            <path d="M10 9V0h12v9H10zm12 5h10v18H0V14h10v9h12v-9z" />
          </svg>
          Search Unsplash
        </button>
      </div>

      <div ref={holderRef} className="min-h-[400px] focus-within:outline-none" />

      {showUnsplash && (
        <UnsplashModal
          onSelect={handleUnsplashSelect}
          onClose={() => setShowUnsplash(false)}
        />
      )}
    </div>
  );
}
