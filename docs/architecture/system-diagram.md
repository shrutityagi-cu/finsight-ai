# FinSight AI System Architecture

```text
                  User
                    │
                    ▼
            Next.js Frontend
                    │
                    ▼
              FastAPI Backend
     ┌──────────────┼───────────────┐
     ▼              ▼               ▼
Authentication   Portfolio      AI Services
     │              │               │
     ▼              ▼               ▼
 PostgreSQL     ML Engine     OpenAI API
                    │
                    ▼
             Financial APIs
      (Yahoo Finance / Alpha Vantage)
```