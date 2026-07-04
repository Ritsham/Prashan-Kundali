# ॐ Kundali Studio (Prashna & Lagna Engine)

An advanced, premium Vedic Astrology SaaS platform combining high-precision astronomical calculations (Swiss Ephemeris + Lahiri Ayanamsa) with an interpretation engine, a real-time astrologer community board, and practitioner workspaces.

The project is styled under the theme of **Modern Indian Luxury**—drawing visual inspiration from ancient astronomical observatories like Jantar Mantar and the Indian Museum of Astronomy, combined with clean, high-end interfaces.

---

## 🌌 Core Features

### 1. Calculation Engine (Swiss Ephemeris & Ayanamsa)
- **High-Precision calculations**: Leverages `pyswisseph` (C-ephemeris wrapper) to compute exact planetary coordinates, whole-sign house structures, and planetary degrees.
- **Divisional Charts (Vargas)**: Generates D1 (Lagna Chart) and D9 (Navamsha Chart) layouts dynamically.
- **Nakshatra & Pada Mapping**: Calculates Nakshatra divisions, padas, and planetary rulers.
- **Vimshottari Dasha**: Computes full 120-year three-tier Dasha structures (Maha Dasha, Antar Dasha, Pratyantar Dasha) based on moon coordinates.
- **Timezone Detection**: Uses `timezonefinder` and coordinate lookups to automatically resolve standard UTC offsets for local times.

### 2. Modern Indian Luxury Frontend
- **Obsensory Aesthetics**: Curated gold-and-cream HSL color systems, Marcellus serif typography, and glassmorphism elements.
- **Ambient Elements**: Includes a dynamically rotating background **Sudarshan Chakra** SVG and a golden **Lord Ganesha** icon integrated into the global navigation bar logo.
- **Fully Modular**: Vanilla ES6 JavaScript sub-modules (`app.js`, `state.js`, `api.js`, `auth.js`, `flash.js`) running without massive build-step overheads.
- **Global Toast Notification System**: Animated, slide-in toast notifications capturing WebSocket errors, API failures, and unhandled promise rejections.

### 3. Consultation Workspace & Queues
- **Consultant Console (`consultant.html`)**: Real-time practitioner panels allowing verified astrologers to view pending questions, review astronomical snapshots of client situations, draft interpretations, and manage refunds.
- **Admin Verification Portal (`admin.html`)**: Interactive queue allowing admins to approve or reject pending astrologer validation requests.
- **Application Portal (`apply.html`)**: Profile creation form for astrologers seeking platform verification.

### 4. Real-Time Astro Board Community
- **WebSocket Chat Room (`community.html`)**: Collaborative workspace featuring live channels, multi-threaded sub-replies, starred messages, custom display names, and file/chart uploads.

### 5. Validation QA Console (`validation.html`)
- A dedicated testing workspace to cross-verify calculated charts, degrees, and Nakshatras against industry benchmark values.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend Framework** | FastAPI (Python 3.11+, ASGI), Uvicorn |
| **Astro calculations** | PySwissEph (Swiss Ephemeris), TimezoneFinder |
| **Database & Cache** | SQLite (via `aiosqlite` async drivers), Redis |
| **Authentication & AuthZ** | Supabase OAuth & Row-Level Security (RLS) |
| **Real-Time Communication** | Native WebSockets |
| **AI Interpretation** | Multi-key rotated LLM providers (Gemini / OpenAI) |
| **Frontend Foundation** | HTML5, CSS3 Variables, Vanilla ES6 JavaScript modules |

---

## 🚀 Setup & Installation

### Prerequisite: Ephemeris Data
The calculation engine uses Swiss Ephemeris binary files to compute coordinates. Run the built-in downloader script to pull the required astronomical ephemerides before launching:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/download_ephemeris.py
```
This populates the local `ephemeris/` directory with `sepl_18.se1`, `semo_18.se1`, and `seas_18.se1`.

### Environment Configuration (`.env`)
Create a `.env` file in the root directory (based on `.env.example`):

```ini
# Supabase Integration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# AI Interpretation API Keys
PRASHNA_LLM_PROVIDER=gemini # Options: gemini, openai
GEMINI_API_KEYS=AIzaSyA1...,AIzaSyA2...
GEMINI_INTERPRETATION_MODEL=gemini-2.0-flash

# Optional OpenAI keys
OPENAI_API_KEYS=sk-proj-...,sk-proj-...
OPENAI_INTERPRETATION_MODEL=gpt-4o
```

### Launching the Application
Launch the ASGI development server:

```bash
python3 main.py
```

The server will run at `http://127.0.0.1:8000`.

- **Main Platform**: `http://127.0.0.1:8000/index.html`
- **Validation Console**: `http://127.0.0.1:8000/validation.html`
- **Admin Verification Panel**: `http://127.0.0.1:8000/admin.html`
- **Astrologer Board**: `http://127.0.0.1:8000/community.html`

---

## 📂 Codebase Architecture

```
├── app/
│   ├── api/                   # FastAPI Endpoints
│   │   ├── admin.py           # Admin queue controls
│   │   ├── community.py       # Community chat logs
│   │   ├── consultants.py     # Consultant directory queries
│   │   ├── prashna.py         # Lagna & Prashna chart API
│   │   └── validation.py      # Calculations verification
│   ├── astrology/             # Core Astronomy Calculations
│   │   ├── constants.py       # Ayanamsa & degree indices
│   │   ├── divisional.py      # Vargas (D1/D9) computation
│   │   ├── vimshottari.py     # Vimshottari Dasha calculations
│   │   └── zodiac.py          # Rashi & Nakshatra mapping
│   ├── services/              # Business Logic
│   │   ├── answer_generator.py # Rule-based & LLM interpretations
│   │   ├── chart_calculator.py# High-precision coordinates
│   │   ├── geocoding_service.py# Nominatim geographic queries
│   │   └── realtime.py        # WebSocket channel management
│   └── storage/               # SQLite database access
├── frontend/                  # Static Web Assets
│   ├── index.html             # Homepage & calculation entry
│   ├── community.html         # WebSocket Astrologer Board
│   ├── consultant.html        # Live consultation dashboard
│   ├── styles.css             # Main stylesheet & design system
│   ├── community.css          # Astro Board messaging styles
│   ├── app.js                 # Global coordinate and lagna launcher
│   ├── community.js           # Live WebSocket chat module
│   ├── auth.js                # Supabase session synchronize helper
│   ├── auth-shared.js         # Unified Supabase Auth module
│   └── flash.js               # Premium toast alerts
├── main.py                    # Application Entrypoint & WS Mounts
└── requirements.txt           # Python Dependency Manifest
```

---

## 📡 API Reference & WebSockets

### REST API Endpoints

#### `POST /api/prashna`
Calculates an astrological chart and returns rule-based/AI interpretations.
- **Request Body**:
  ```json
  {
    "question": "Will I get my dream job this year?",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "place_name": "New Delhi, Delhi, India"
  }
  ```
- **Response Elements**: Includes house placements (1-12), planetary degrees, Nakshatras, current Vimshottari Dasha lords, and a structured `interpretation.answer` section.

#### `GET /api/admin/pending-astrologers`
Retrieves pending verification profiles (Admin authentication token required).

---

### WebSocket Gateways

#### Astro Board Channels
- **URL Path**: `/ws/community/{channel_name}`
- **Sub-actions**:
  - `send_message`: Broadcasts a text message/chart image payload.
  - `send_thread_reply`: Appends message logs into a child thread tree.
  - `star_message`: Likes/stars a message thread.
  - `delete_message`: Soft-deletes a message.

#### Live Consultations
- **URL Path**: `/ws/consultation/{booking_id}`
- **Usage**: Encrypted real-time chat sync between consulting clients and practitioners.

---

## 🔒 Security & Verification

- **Supabase JWTs**: Restricts access to sensitive workspaces (Admin dashboard, Consultant portal, Astro Board) to users carrying verified roles.
- **Row-Level Security (RLS)**: Enforced database schemas to prevent unapproved profile reads or modifications.
- **Client Side Guards**: Verified sessions are validated client-side in [auth-shared.js](file:///c:/Users/gyanr/Desktop/Kundli/Prashan-Kundali/frontend/auth-shared.js) prior to rendering protected elements.

---

## ॐ Subhamastu
