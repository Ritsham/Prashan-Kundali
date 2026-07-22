# Verified Astrologer Community Platform - Architecture Overview

## Overview
The Verified Astrologer Community Platform is a private, real-time discussion space integrated into the existing Kundali platform. It allows verified astrologers to discuss charts, share knowledge across systems (Vedic, KP, Prashna), and collaborate.

## Tech Stack
* **Frontend:** Vanilla HTML/JS/CSS (No build tools required for core logic).
* **Backend:** FastAPI (Python).
* **Database & Auth:** Supabase (PostgreSQL & GoTrue).
* **Real-time:** FastAPI WebSockets combined with Supabase for persistence.

## Database Schema Highlights
The platform uses the following key tables:
* `community_profiles`: User metadata, specialties, systems practiced, and bios for astrologers.
* `community_channels`: The available topic channels (e.g., `#general-discussion`, `#prashna-astrology`).
* `channel_memberships`: Tracks which channels a user has joined.
* `community_messages`: The core messages table. Supports `content_type` (`STANDARD`, `PRASHNA_CASE`, `LAGNA_CASE`) and links to `chart_id` for custom chart discussion posts.
* `community_threads`: Nested replies to a specific `community_message`.
* `message_reactions`: Tracks user reactions to posts (e.g., "Insightful", "Helpful").
* `thread_follows`: Tracks users following a thread for notifications.
* `community_reports`: Stores moderation flags submitted by users.
* `community_notifications`: Stores notifications for mentions, replies, and reactions.

## Frontend Architecture
The community frontend is a single-page application built primarily inside `community.html` and powered by `community.js`.

### Key Components
1. **Left Sidebar:** Displays the navigation links (Channels, Members Directory, Notifications).
2. **Center Content (Feed):** The main area where messages are loaded. It dynamically switches between the channel message feed, the Members Directory grid, and the Notifications list based on user interaction.
3. **Right Context Panel:** A slide-out (desktop-sticky) panel used for deep-diving into specific contexts without losing place in the main feed. Used for:
   * **Threads:** Viewing and replying to nested conversations.
   * **User Profiles:** Viewing another astrologer's detailed profile.

### Chart Integration
Users can seamlessly share charts directly from the Lagna/Prashna generation flows. 
1. In `app.js`, when a chart is rendered, the "Share to Community" button appears.
2. Clicking it opens a modal allowing the user to select a community channel and attach a comment.
3. It makes a `POST` request to `/api/community/messages/{channel}` with `content_type` set to the respective chart type.
4. `community.js` detects these special `content_type`s in the feed and renders them as "Chart Discussion Cards".

## WebSocket Implementation
Real-time communication is managed by a FastAPI `ConnectionManager` inside `app/api/community.py`.

* **Connection:** Clients connect to `ws://.../api/community/ws/{channel_name}` and send `{"action":"authenticate","token":"<jwt>"}` as the first WebSocket message.
* **Authentication:** The token is validated using Supabase Auth and is never placed in the WebSocket URL.
* **Broadcasting:** When a user sends a message, adds a reaction, or replies to a thread, the backend persists the change to Supabase and immediately broadcasts the event (e.g., `new_message`, `reaction_updated`, `new_thread_reply`) to all connected clients in that channel.
* **State Updates:** `community.js` parses incoming WebSocket events and dynamically updates the DOM to reflect new messages, reply counts, or reactions without requiring a full page refresh.

## Security & Moderation
* **Authentication:** All API routes rely on `RequireVerifiedAstrologer()`, a FastAPI dependency that verifies the JWT and ensures the user has an approved `community_profile`.
* **Moderation:** Users can report posts. Admins have access to a dedicated dashboard (`admin-community-moderation.html`) protected by `RequireRole("admin")`, where they can soft-delete posts or ban users.
