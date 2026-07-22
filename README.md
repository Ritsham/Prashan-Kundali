# Shree Lakshmi Astro (Prashna & Lagna Engine)

An advanced, premium Vedic Astrology SaaS platform combining high-precision astronomical calculations (Swiss Ephemeris + Lahiri Ayanamsa) with an AI-driven interpretation engine, a real-time WebSocket-powered astrologer community board, and professional practitioner workspaces.

The platform is designed with a **Modern Indian Luxury** aesthetic—drawing visual inspiration from ancient astronomical observatories like Jantar Mantar and the Indian Museum of Astronomy, combined with clean, high-end interfaces, gold-and-cream HSL color systems, serif typography, and glassmorphism elements.

---

## 🌌 Core Features

### 1. Calculation Engine (Swiss Ephemeris & Ayanamsa)
- **High-Precision Coordinates**: Uses `pyswisseph` (C-ephemeris wrapper) to compute exact planetary positions, whole-sign house coordinates, and degrees.
- **Divisional Charts (Vargas)**: Dynamically generates D1 (Lagna Chart) and D9 (Navamsha Chart) layouts.
- **Nakshatra & Pada Mapping**: Calculates exact Nakshatra divisions, padas, and planetary rulers.
- **Vimshottari Dasha**: Computes full 120-year three-tier Dasha structures (Maha Dasha, Antar Dasha, Pratyantar Dasha) based on moon coordinates.
- **Timezone Resolver**: Uses `timezonefinder` and geographical coordinates to automatically determine exact UTC offsets for any location.

### 2. Frontends Served by FastAPI
- **Canonical Public Website**: The public landing, Prashna/Lagna flow, consultation intake, matchmaking, policy pages, and supporting static pages are served from `frontend_old/`.
- **React Workspaces**: Payment, Astro Community, and Admin workspace screens are built from `frontend/` and served from `frontend/dist/` on their explicit routes.
- **Luxury Spiritual Aesthetic**: Styled with curated gold-and-cream palettes, traditional brand elements, and an integrated Lord Ganesha icon in the navigation header.
- **Production Routes**: FastAPI serves the legacy public platform at `/` and `/index.html`; `/payment`, `/astro-community`, and `/admin` require the React build output.

### 3. Consultation Workspaces & Queues
- **Consultant Directory & Profiles**: Interactive search and detailed practitioner dashboards.
- **Admin Verification Portal**: Review and approve pending astrologer registration requests.
- **Real-Time Client Consultation Workspaces**: Secure chat channels for clients and astrologers during consultations.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend Framework** | FastAPI (Python 3.11+, ASGI), Uvicorn |
| **Astro Calculations** | PySwissEph (Swiss Ephemeris), TimezoneFinder |
| **Database & Cache** | Supabase Postgres, Supabase Storage, optional Redis |
| **Authentication & AuthZ** | Supabase Auth, Row-Level Security (RLS) policies |
| **Real-Time Layer** | Native WebSockets |
| **AI Interpretation** | Multi-key rotated LLM providers (Gemini / OpenAI) |
| **Frontend** | Static HTML/CSS/JS in `frontend_old/`, plus React/Vite workspaces in `frontend/` |

---

## 🚀 Setup & Installation

### Prerequisite: Ephemeris Data
The calculation engine uses Swiss Ephemeris binary files to compute coordinates. Run the built-in downloader script to pull the required astronomical ephemerides before launching:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/download_ephemeris.py
```
This populates the local `ephemeris/` directory with `sepl_18.se1`, `semo_18.se1`, and `seas_18.se1`.

### Environment Configuration
Create the backend environment file from the example:

```bash
cp .env.example .env
```

Backend secrets such as `SUPABASE_SERVICE_ROLE_KEY`, LLM provider keys, Redis credentials, and Razorpay secrets must stay in backend/server environment storage only.

See [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) for development, staging, and production requirements.

### Launching the Application
Build the React workspace bundle when you need `/payment`, `/astro-community`, or `/admin`:

```bash
cd frontend
npm install
npm run build
cd ..
```

Launch the ASGI development server:

```bash
python3 main.py
```

The server will run locally at `http://127.0.0.1:8000`.

- **Main Application & Pages**: `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/index.html` served from `frontend_old/`
- **React Workspace Pages**: `http://127.0.0.1:8000/payment`, `/astro-community`, and `/admin` served from `frontend/dist/`

---

## 📂 Codebase Architecture

```
├── app/
│   ├── api/                   # FastAPI Endpoints
│   │   ├── admin_metrics.py   # Admin metrics logs
│   │   ├── astrologer.py      # Astrologer verification controllers
│   │   ├── community.py       # Community chat logs
│   │   ├── consultants.py     # Consultant directory queries
│   │   ├── consultation.py    # Consultation booking handlers
│   │   ├── matchmaking.py     # Compatibility reporting
│   │   └── prashna.py         # Lagna & Prashna chart APIs
│   ├── astrology/             # Core Astronomy Calculations
│   │   ├── constants.py       # Ayanamsa & degree indices
│   │   ├── divisional.py      # Vargas (D1/D9) computation
│   │   ├── vimshottari.py     # Vimshottari Dasha calculations
│   │   └── zodiac.py          # Rashi & Nakshatra mapping
│   ├── services/              # Business Logic
│   │   ├── answer_generator.py # Rule-based & LLM interpretations
│   │   ├── chart_calculator.py# High-precision coordinates
│   │   ├── geocoding_service.py# Nominatim geographic queries
│   │   └── realtime.py        # WebSocket connection manager
│   └── storage/               # SQLite & Supabase access helpers
├── frontend_old/              # Canonical public website and legacy app flows
│   ├── index.html             # Landing page
│   ├── consultation.html      # Consultant/payment flow page
│   ├── styles.css             # Shared site styling
│   └── *.js                   # Browser-side page scripts
├── frontend/                  # React/Vite payment, community, and admin workspaces
│   ├── src/                   # React application source
│   └── dist/                  # Built assets served by FastAPI after npm run build
├── main.py                    # Application Entrypoint & WS Mounts
└── requirements.txt           # Python Dependency Manifest
```

---

## 📡 API Reference & WebSockets

### REST API Endpoints

#### `POST /api/prashna`
Calculates an astrological chart and returns rule-based/AI interpretations.

**Request Body:**
```json
{
  "question": "Will I get my dream job this year?",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "place_name": "New Delhi, Delhi, India"
}
```

**Response Elements:** Includes house placements (1-12), planetary degrees, Nakshatras, current Vimshottari Dasha lords, and a structured `interpretation.answer` section.

#### `GET /api/admin/pending-astrologers`
Retrieves pending verification profiles (Admin authentication token required).

---

## 🔄 WebSocket Event Protocol

The platform implements real-time WebSockets to synchronize chat logs, threaded replies, reactions, and online statuses.

### WebSocket Gateways
- **Astro Board Channels**: `/ws/community/{channel_name}`
- **Live Consultations**: `/ws/consultation/{booking_id}`

### Message Flows

```mermaid
sequenceDiagram
    autonumber
    actor Astrologer as Astrologer Client
    actor Client as Standard Client
    participant Server as FastAPI Server
    database DB as Supabase DB

    Note over Astrologer, Server: WebSocket Handshake & Connection
    Astrologer->>Server: Connect to /ws/community/{channel}
    Astrologer->>Server: { "action": "authenticate", "token": "<Supabase JWT>" }
    activate Server
    Server->>Server: Validate Supabase JWT and Role
    Server-->>Astrologer: Connection Established (ACK)

    Note over Astrologer, Server: Event: send_message
    Astrologer->>Server: { "action": "send_message", "content": "Daily horoscope update...", "chart_id": "123" }
    Server->>DB: Save message to community_messages
    DB-->>Server: Message saved successfully (id: msg_789)
    Server-->>Astrologer: Broadcast payload: { "type": "new_message", "message": "..." }
    Server-->>Client: Broadcast payload: { "type": "new_message", "message": "..." }

    Note over Client, Server: Event: toggle_reaction
    Client->>Server: { "action": "toggle_reaction", "message_id": "msg_789", "reaction_type": "helpful" }
    Server->>DB: Update user reaction state
    Server-->>Astrologer: Broadcast: { "type": "reaction_updated", "message_id": "msg_789", "reaction_type": "helpful" }
    Server-->>Client: Broadcast: { "type": "reaction_updated", "message_id": "msg_789", "reaction_type": "helpful" }
    deactivate Server
```

---

## 🔒 Security & Verification

- **Supabase JWTs**: Restricts access to sensitive workspaces (Admin dashboard, Astro Board) to users carrying verified roles.
- **Row-Level Security (RLS)**: Enforced database schemas to prevent unapproved profile reads or modifications.
- **Client Side Guards**: Browser-side scripts validate sessions and roles before rendering protected controls.

---

## ॐ Subhamastu
