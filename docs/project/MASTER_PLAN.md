# FinSight AI — Master Engineering Plan

## Vision

Build an institutional-grade AI-powered investment research platform with production-quality architecture, strong security, explainable machine learning, and scalable cloud deployment.

---

# Tech Stack

## Backend

- Python 3.12
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Pydantic v2
- JWT Authentication
- AsyncIO

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- Zustand
- TanStack Query

## AI

- RAG
- OpenAI
- LangChain
- Financial News Analysis

## ML

- Scikit-learn
- XGBoost
- LightGBM
- TensorFlow

---

# Architecture

Frontend

↓

FastAPI API

↓

Services

↓

Repositories

↓

PostgreSQL

↓

ML + AI Layer

---

# Engineering Rules

No business logic inside routes.

No SQL inside routes.

No SQL inside services.

Repositories own persistence.

Services own business logic.

Routes own HTTP.

Schemas own validation.

Models own persistence.

---

# Current Sprint

Sprint 1

Status

In Progress

---

# Backend Progress

✅ Project scaffold

✅ Database schema

✅ ORM models

⬜ Alembic migrations

⬜ Authentication

⬜ Portfolio CRUD

⬜ Watchlists

⬜ Prediction Engine

⬜ News Engine

⬜ AI Assistant

---

# Frontend Progress

⬜ Next.js setup

⬜ Authentication

⬜ Dashboard

⬜ Portfolio

⬜ Watchlist

⬜ Predictions

⬜ Chat

---

# ML Progress

⬜ Dataset pipeline

⬜ Feature Engineering

⬜ Model Training

⬜ Model Registry

⬜ Inference Service

---

# DevOps

⬜ Docker

⬜ Docker Compose

⬜ GitHub Actions

⬜ Azure Deployment

⬜ Monitoring

---

# Technical Debt

None approved.

---

# Rule

Every new feature must include:

- Tests

- Documentation

- Error handling

- Logging

- Type hints

- API schema