# Medium Clone — Full Project Specification for Claude Code

## Project Overview

Build a full-stack blogging platform inspired by Medium. Users can sign up, write and publish articles using a block-based editor, follow their favorite creators, and engage with content through likes, comments, and social sharing. Articles are shareable via unique links and optimized for SEO.

---

## Tech Stack (strictly enforced)

| Layer         | Technology               | Notes                                          |
|---------------|--------------------------|------------------------------------------------|
| Frontend      | Next.js 14+ (App Router) | TypeScript, Tailwind CSS, server components    |
| Text Editor   | Editor.js                | Block-based rich text, output stored as JSONB  |
| Backend API   | FastAPI (Python 3.11+)   | Async, Pydantic v2 for validation              |
| Database      | PostgreSQL 15+           | Raw SQL via asyncpg — **NO ORM**               |
| Auth          | JWT (python-jose)        | Access + refresh token pattern with httpOnly cookies |
| Image Storage | Cloudflare R2 or local   | For avatars, cover images, embedded images     |
| Deployment    | Vercel (frontend) + Render (backend) | Free tiers                        |

**Hard constraints:**
- Everything must be open source and free.
- Do NOT use any ORM (no SQLAlchemy, no Prisma, no Drizzle). All database access is raw SQL through asyncpg.
- Do NOT use Django, Flask, or Express. Backend is FastAPI only.
- Do NOT use any paid services or proprietary tools.

---

## Project Structure

```
medium-clone/
├── frontend/                    # Next.js application
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                    # Landing page (logged out) / redirect to feed (logged in)
│   │   │   ├── layout.tsx                  # Root layout with navbar
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx          # Login form
│   │   │   │   └── signup/page.tsx         # Signup form
│   │   │   ├── feed/page.tsx               # Personalized feed (articles from followed creators)
│   │   │   ├── explore/page.tsx            # All published articles, trending, search
│   │   │   ├── blog/[slug]/page.tsx        # Single article view (SSR for SEO)
│   │   │   ├── editor/page.tsx             # New article (Editor.js)
│   │   │   ├── editor/[id]/page.tsx        # Edit existing article
│   │   │   ├── user/[username]/page.tsx    # Public profile page
│   │   │   └── settings/page.tsx           # Edit own profile
│   │   ├── components/
│   │   │   ├── Navbar.tsx                  # Top navigation bar
│   │   │   ├── ArticleCard.tsx             # Article preview card for feeds
│   │   │   ├── EditorComponent.tsx         # Editor.js wrapper (client component)
│   │   │   ├── EditorRenderer.tsx          # Renders Editor.js JSONB blocks as HTML
│   │   │   ├── CommentSection.tsx          # Comments list + comment form
│   │   │   ├── LikeButton.tsx              # Like/unlike toggle with count
│   │   │   ├── FollowButton.tsx            # Follow/unfollow toggle
│   │   │   ├── ShareButton.tsx             # Social sharing dropdown
│   │   │   └── ProtectedRoute.tsx          # Auth guard wrapper
│   │   ├── lib/
│   │   │   ├── api.ts                      # Axios/fetch wrapper for backend API calls
│   │   │   ├── auth.ts                     # Token management, auth context
│   │   │   └── types.ts                    # Shared TypeScript types
│   │   └── styles/
│   │       └── globals.css                 # Tailwind base + custom article styles
│   ├── public/                             # Static assets
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── backend/                     # FastAPI application
│   ├── main.py                             # App entry, CORS, lifespan (pool init/close)
│   ├── config.py                           # Environment variables via pydantic-settings
│   ├── db.py                               # asyncpg connection pool management
│   ├── auth.py                             # JWT creation, verification, password hashing
│   ├── dependencies.py                     # FastAPI dependencies (get current user, etc.)
│   ├── models.py                           # Pydantic schemas (request/response models only, NOT ORM)
│   ├── utils.py                            # Slug generation, pagination helpers
│   ├── routes/
│   │   ├── auth_routes.py                  # POST /auth/signup, POST /auth/login, POST /auth/refresh
│   │   ├── user_routes.py                  # GET /users/{username}, PATCH /users/me
│   │   ├── post_routes.py                  # Full CRUD for articles
│   │   ├── comment_routes.py               # Create, list, delete comments
│   │   ├── like_routes.py                  # Toggle like, get like count
│   │   └── follow_routes.py                # Follow/unfollow, get followers/following lists
│   ├── requirements.txt
│   └── .env                                # DATABASE_URL, JWT_SECRET, etc.
│
└── database/
    └── migrations/
        ├── 001_initial_schema.sql          # Users, posts, comments, likes, follows tables
        └── 002_indexes.sql                 # Performance indexes
```

---

## Database Schema (raw SQL — no ORM)

Use these exact table definitions. Run them directly against PostgreSQL.

```sql
-- 001_initial_schema.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    avatar_url TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(300) NOT NULL,
    slug VARCHAR(350) UNIQUE NOT NULL,
    subtitle VARCHAR(500) NOT NULL DEFAULT '',
    content JSONB NOT NULL DEFAULT '{}',           -- Editor.js block data
    cover_image_url TEXT NOT NULL DEFAULT '',
    published BOOLEAN NOT NULL DEFAULT FALSE,
    reading_time_minutes INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE likes (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, post_id)
);

CREATE TABLE follows (
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (follower_id, following_id),
    CHECK (follower_id != following_id)  -- prevent self-follow
);

-- 002_indexes.sql

CREATE INDEX idx_posts_author ON posts(author_id);
CREATE INDEX idx_posts_slug ON posts(slug);
CREATE INDEX idx_posts_published_date ON posts(published, created_at DESC);
CREATE INDEX idx_comments_post ON comments(post_id, created_at ASC);
CREATE INDEX idx_comments_user ON comments(user_id);
CREATE INDEX idx_likes_post ON likes(post_id);
CREATE INDEX idx_likes_user ON likes(user_id);
CREATE INDEX idx_follows_follower ON follows(follower_id);
CREATE INDEX idx_follows_following ON follows(following_id);
```

---

## Backend API Endpoints

All endpoints return JSON. Use Pydantic v2 models for request validation and response serialization. Every database query must use raw SQL with asyncpg parameterized queries ($1, $2, etc.) — never string formatting.

### Authentication

| Method | Endpoint          | Auth? | Description                                      |
|--------|-------------------|-------|--------------------------------------------------|
| POST   | /auth/signup      | No    | Create account. Hash password with bcrypt. Return access + refresh tokens. |
| POST   | /auth/login       | No    | Verify email + password. Return access + refresh tokens. |
| POST   | /auth/refresh     | No    | Accept refresh token, return new access token.   |
| GET    | /auth/me          | Yes   | Return current user profile from JWT.            |

- Access tokens expire in 30 minutes.
- Refresh tokens expire in 7 days.
- Passwords hashed with passlib bcrypt.
- JWT signed with HS256 using a secret from environment variable `JWT_SECRET`.

### Posts (Articles)

| Method | Endpoint              | Auth? | Description                                              |
|--------|-----------------------|-------|----------------------------------------------------------|
| POST   | /posts                | Yes   | Create new post (draft or published). Auto-generate slug from title. |
| GET    | /posts                | No    | List published posts. Supports `?page=1&limit=10&author=username&search=keyword`. |
| GET    | /posts/{slug}         | No    | Get single post by slug. Include author info, like count, whether current user liked it. |
| PATCH  | /posts/{id}           | Yes   | Update own post (title, content, published status, cover image). |
| DELETE | /posts/{id}           | Yes   | Delete own post.                                         |
| GET    | /feed                 | Yes   | Get posts from followed creators, ordered by newest. Paginated. |

- Slug generation: lowercase title, replace spaces with hyphens, strip special characters, append short random suffix for uniqueness.
- `content` field stores Editor.js JSON output directly as JSONB.
- `reading_time_minutes`: calculate on save by counting words in text blocks (average 200 words/min).

### Comments

| Method | Endpoint                     | Auth? | Description                         |
|--------|------------------------------|-------|-------------------------------------|
| POST   | /posts/{post_id}/comments    | Yes   | Add a comment to a post.            |
| GET    | /posts/{post_id}/comments    | No    | List comments for a post, with author info. Paginated, oldest first. |
| DELETE | /comments/{id}               | Yes   | Delete own comment.                 |

### Likes

| Method | Endpoint                 | Auth? | Description                                    |
|--------|--------------------------|-------|------------------------------------------------|
| POST   | /posts/{post_id}/like    | Yes   | Toggle like. If already liked, unlike. Return new like count and liked status. |
| GET    | /posts/{post_id}/likes   | No    | Get like count and list of users who liked.    |

### Follows

| Method | Endpoint                         | Auth? | Description                              |
|--------|----------------------------------|-------|------------------------------------------|
| POST   | /users/{user_id}/follow          | Yes   | Toggle follow. If already following, unfollow. |
| GET    | /users/{username}/followers      | No    | List followers of a user. Paginated.     |
| GET    | /users/{username}/following      | No    | List who a user follows. Paginated.      |

### Users

| Method | Endpoint              | Auth? | Description                                      |
|--------|-----------------------|-------|--------------------------------------------------|
| GET    | /users/{username}     | No    | Public profile: display name, bio, avatar, post count, follower/following counts. |
| PATCH  | /users/me             | Yes   | Update own profile (display_name, bio, avatar_url). |

---

## Backend Implementation Details

### Database Connection (db.py)

```python
import asyncpg
from config import settings

pool: asyncpg.Pool | None = None

async def init_pool():
    global pool
    pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10
    )

async def close_pool():
    global pool
    if pool:
        await pool.close()

async def get_pool() -> asyncpg.Pool:
    assert pool is not None, "Database pool not initialized"
    return pool
```

### App Lifespan (main.py)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from db import init_pool, close_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()

app = FastAPI(title="Medium Clone API", lifespan=lifespan)
```

### Query Pattern (example)

All queries follow this pattern — raw SQL, parameterized, using asyncpg directly:

```python
async def get_post_by_slug(slug: str, current_user_id: str | None = None):
    pool = await get_pool()
    row = await pool.fetchrow("""
        SELECT p.*, u.username, u.display_name, u.avatar_url,
               COUNT(DISTINCT l.user_id) AS like_count,
               COUNT(DISTINCT c.id) AS comment_count,
               BOOL_OR(l.user_id = $2) AS liked_by_current_user
        FROM posts p
        JOIN users u ON p.author_id = u.id
        LEFT JOIN likes l ON l.post_id = p.id
        LEFT JOIN comments c ON c.post_id = p.id
        WHERE p.slug = $1 AND p.published = TRUE
        GROUP BY p.id, u.id
    """, slug, current_user_id)
    return dict(row) if row else None
```

---

## Frontend Implementation Details

### Editor.js Integration

The Editor.js component must be a **client component** (`"use client"`) because Editor.js requires the DOM. Wrap it in a dynamic import with `ssr: false`.

```typescript
// components/EditorComponent.tsx
"use client";
import { useEffect, useRef } from "react";
import EditorJS, { OutputData } from "@editorjs/editorjs";
import Header from "@editorjs/header";
import List from "@editorjs/list";
import Quote from "@editorjs/quote";

interface Props {
  data?: OutputData;
  onChange: (data: OutputData) => void;
}

export default function EditorComponent({ data, onChange }: Props) {
  const editorRef = useRef<EditorJS | null>(null);

  useEffect(() => {
    if (!editorRef.current) {
      const editor = new EditorJS({
        holder: "editorjs",
        data: data || undefined,
        tools: {
          header: { class: Header, config: { levels: [2, 3, 4] } },
          list: { class: List },
          quote: { class: Quote },
        },
        onChange: async () => {
          const savedData = await editor.save();
          onChange(savedData);
        },
      });
      editorRef.current = editor;
    }
    return () => {
      editorRef.current?.destroy();
      editorRef.current = null;
    };
  }, []);

  return <div id="editorjs" className="prose max-w-none" />;
}
```

### Editor.js Block Renderer

For the article reading page, render the stored JSONB blocks back to HTML:

```typescript
// components/EditorRenderer.tsx
import { OutputData } from "@editorjs/editorjs";

export default function EditorRenderer({ data }: { data: OutputData }) {
  return (
    <article className="prose lg:prose-lg max-w-none">
      {data.blocks.map((block, index) => {
        switch (block.type) {
          case "paragraph":
            return <p key={index} dangerouslySetInnerHTML={{ __html: block.data.text }} />;
          case "header":
            const Tag = `h${block.data.level}` as keyof JSX.IntrinsicElements;
            return <Tag key={index}>{block.data.text}</Tag>;
          case "list":
            const ListTag = block.data.style === "ordered" ? "ol" : "ul";
            return (
              <ListTag key={index}>
                {block.data.items.map((item: string, i: number) => (
                  <li key={i} dangerouslySetInnerHTML={{ __html: item }} />
                ))}
              </ListTag>
            );
          case "quote":
            return (
              <blockquote key={index}>
                <p>{block.data.text}</p>
                {block.data.caption && <cite>{block.data.caption}</cite>}
              </blockquote>
            );
          case "image":
            return <img key={index} src={block.data.url} alt={block.data.caption || ""} />;
          default:
            return null;
        }
      })}
    </article>
  );
}
```

### Social Sharing

Implement sharing via URL-based share links (no API keys needed):

```typescript
// components/ShareButton.tsx
const shareLinks = {
  twitter: (url: string, title: string) =>
    `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`,
  linkedin: (url: string) =>
    `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
  facebook: (url: string) =>
    `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
  copyLink: (url: string) => navigator.clipboard.writeText(url),
};
```

### SEO Meta Tags

Every article page must generate proper meta tags for social sharing previews:

```typescript
// app/blog/[slug]/page.tsx
export async function generateMetadata({ params }): Promise<Metadata> {
  const post = await fetchPost(params.slug);
  return {
    title: post.title,
    description: post.subtitle || post.title,
    openGraph: {
      title: post.title,
      description: post.subtitle,
      images: post.cover_image_url ? [post.cover_image_url] : [],
      type: "article",
      authors: [post.author_display_name],
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.subtitle,
    },
  };
}
```

### Auth Flow in Frontend

- Store JWT access token in memory (React context/state), NOT localStorage.
- Store refresh token in an httpOnly cookie (set by the backend).
- On app load, call `/auth/refresh` to get a new access token silently.
- Attach access token to every API request via an Axios/fetch interceptor.
- On 401 response, try refreshing. If refresh fails, redirect to login.

---

## API Response Formats

### Successful response

```json
{
  "id": "uuid",
  "title": "My Article",
  "slug": "my-article-a1b2c3",
  "content": { "blocks": [...] },
  "author": {
    "username": "johndoe",
    "display_name": "John Doe",
    "avatar_url": "https://..."
  },
  "like_count": 42,
  "comment_count": 7,
  "liked_by_me": true,
  "reading_time_minutes": 5,
  "published": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Paginated list response

```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "limit": 10,
  "has_next": true
}
```

### Error response

```json
{
  "detail": "Post not found"
}
```

Use FastAPI's `HTTPException` for all errors with appropriate status codes (400, 401, 403, 404, 409, 422).

---

## Environment Variables

### Backend (.env)

```
DATABASE_URL=postgresql://user:pass@host/dbname
JWT_SECRET=a-long-random-secret-at-least-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
```

### Frontend (.env.local)

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## UI/UX Requirements

- Clean, minimal design similar to Medium. Lots of whitespace, readable typography.
- Use Tailwind CSS `prose` class for article rendering.
- Mobile responsive — all pages must work on mobile.
- Navbar shows: Logo, Search, Write (if logged in), Profile avatar (if logged in), Login/Signup (if not).
- Article cards show: title, subtitle, author avatar + name, reading time, like count, date.
- Article page shows: title, subtitle, cover image, author info + follow button, content, like button, share button, comment section.
- Loading states: skeleton loaders for feeds and articles.
- Toast notifications for actions (published, liked, followed, error).

---

## Build Order

Implement in this exact sequence, completing each step fully before moving to the next:

1. **Backend setup** — FastAPI app with CORS, asyncpg pool, health endpoint
2. **Database** — Run migration SQL against PostgreSQL
3. **Auth system** — Signup, login, JWT, password hashing, /auth/me
4. **Frontend auth pages** — Login, signup forms, auth context, protected routes
5. **Post CRUD backend** — Create, read, update, delete posts with raw SQL
6. **Editor page** — Editor.js integration, save article, publish toggle
7. **Article reading page** — SSR page at /blog/[slug], render Editor.js blocks, SEO meta
8. **Like system** — Toggle like endpoint + LikeButton component
9. **Comment system** — Comment CRUD + CommentSection component
10. **Follow system** — Follow/unfollow + FollowButton + personalized feed
11. **User profiles** — Public profile page, settings page, edit profile
12. **Explore + search** — Browse all articles, search by keyword
13. **Social sharing** — Share button with Twitter/LinkedIn/Facebook/copy link
14. **Polish** — Loading states, error handling, responsive design, deploy

---

## Quality Requirements

- All SQL queries must use parameterized arguments ($1, $2) — never f-strings or string concatenation.
- All API endpoints must have proper error handling and return appropriate HTTP status codes.
- All form inputs must have client-side validation.
- TypeScript strict mode enabled — no `any` types.
- Every page must be responsive (mobile + desktop).
- Use `async/await` throughout — no blocking calls in FastAPI.
- CORS must be properly configured for the frontend origin.
