# FinSight AI Architecture

# Architecture Style

FinSight AI follows a modular monolithic architecture for Version 1.

This approach balances simplicity with scalability, allowing the project to grow into microservices in future releases if needed.

---

# Why Modular Monolith?

Advantages

- Easier development
- Easier debugging
- Faster deployment
- Single database
- Lower operational complexity
- Ideal for MVPs

Future modules can be extracted into independent services when scaling demands it.

---

# Technology Stack

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- Chart.js

---

## Backend

- FastAPI
- Python
- SQLAlchemy
- Alembic
- Pydantic

---

## Database

- PostgreSQL

---

## AI

- OpenAI API
- LangChain
- FAISS (future RAG)

---

## Machine Learning

- Scikit-learn
- XGBoost
- SHAP

---

## Infrastructure

- Docker
- GitHub Actions
- Azure

---

# Core Principles

- API-first development
- Clean architecture
- Separation of concerns
- Dependency injection
- Type safety
- Test-driven mindset
- Security by design

---

# Project Structure

Frontend

↓

REST API

↓

Business Logic

↓

Database

↓

Machine Learning

↓

AI Services