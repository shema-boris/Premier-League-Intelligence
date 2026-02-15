# Premier League Intelligence System

**AI-powered betting market analysis platform that combines real-time odds data, team news intelligence, and multi-agent reasoning to identify value opportunities in Premier League matches.**

---

## 🎯 Tech Stack

**Backend:**
- Python 3.11+ | FastAPI | CrewAI | Pydantic
- Multi-agent AI orchestration with LangChain
- RESTful API with async request handling

**Frontend:**
- React 18 | TypeScript | TailwindCSS
- Real-time data visualization
- Responsive design with custom component library

**Data Sources & APIs:**
- Football API (RapidAPI) - Historical fixtures, lineups, team statistics
- The Odds API - Live betting market data
- In-memory TTL caching for API optimization

**DevOps:**
- Git version control
- Environment-based configuration
- Modular monorepo architecture (backend/ + frontend/)

---

## ⚡ Key Features

1. **Real-Time Match Intelligence Dashboard**
   - Live upcoming Premier League fixtures with official team badges
   - Date-grouped match display with automatic timezone handling
   - Interactive deep-dive analysis per match

2. **Multi-Dimensional Match Analysis**
   - **Team Form Tracking:** Last 5 matches with W/D/L statistics and goal differentials
   - **Predicted Lineups:** Formation analysis based on recent team selections
   - **Head-to-Head History:** Cross-season encounter analysis (last 3 meetings)

3. **AI-Powered Market Analysis**
   - Multi-agent system analyzing odds discrepancies
   - Team news impact assessment using injury/suspension data
   - Automated report generation with confidence scoring

4. **Prediction Validation & Backtesting**
   - Historical prediction tracking with SQLite persistence
   - Performance metrics calculation (accuracy, ROI, Brier score)
   - Continuous model improvement through result validation

---

## 🔧 The Technical Challenge

**Problem:** Free-tier API limitations made it impossible to fetch historical sports data efficiently. The Football API's free plan restricts critical parameters like `last`, `h2h`, and `search`, forcing inefficient workarounds that would quickly exhaust the 100 requests/day limit.

**Solution:** Implemented a multi-season search strategy with intelligent caching and local filtering:
- Built a season-aware data fetcher that searches backwards through years (2024→2023→2022→2021→2020)
- Replaced restricted parameters with date-range queries and client-side filtering
- Designed an in-memory TTL cache to minimize redundant API calls
- Achieved 80% reduction in API requests while maintaining full feature functionality

This architecture ensures the system works seamlessly within free-tier constraints while delivering enterprise-level features.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ and Node.js 18+
- API Keys: [Football API](https://www.api-football.com/) and [The Odds API](https://the-odds-api.com/)

### Installation

1. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv && venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   
   # Create backend/.env with your API keys
   echo "FOOTBALL_API_KEY=your_key" > .env
   echo "ODDS_API_KEY=your_key" >> .env
   
   # Start server
   python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm start
   ```

3. **Access Application**
   - Frontend: `http://localhost:3000`
   - Backend API: `http://127.0.0.1:8000`
   - API Docs: `http://127.0.0.1:8000/docs`

---

## 📁 Project Architecture

```
Premier-League-Intelligence/
├── backend/                 # Python FastAPI + AI Agents
│   ├── agents/             # CrewAI agent definitions
│   ├── api/                # REST endpoints + caching
│   ├── data_sources/       # External API clients
│   ├── schemas/            # Pydantic models
│   └── validation/         # Backtesting engine
│
└── frontend/               # React + TypeScript
    ├── src/components/     # Reusable UI components
    ├── src/api/           # Backend client
    └── src/types/         # TypeScript interfaces
```

---

## 🎓 Key Learnings & Engineering Decisions

- **API Constraint Handling:** Transformed API limitations into architectural advantages through intelligent caching and client-side processing
- **Multi-Agent Orchestration:** Leveraged CrewAI for parallel analysis workflows with structured output validation
- **Type Safety:** Full TypeScript coverage on frontend with Pydantic validation on backend eliminates runtime errors
- **Separation of Concerns:** Clean backend/frontend split enables independent scaling and deployment.
