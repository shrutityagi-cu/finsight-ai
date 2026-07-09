# Coding Standards

## Python

- Python 3.12

- Ruff

- Black

- mypy

- Async everywhere

---

## FastAPI

Routes

↓

Services

↓

Repositories

↓

Database

Never skip layers.

---

## SQLAlchemy

Use SQLAlchemy 2 style only.

Never use legacy Query API.

Always use select().

---

## Naming

Classes

PascalCase

Functions

snake_case

Files

snake_case

Constants

UPPER_CASE

---

## Imports

Standard Library

↓

Third-party

↓

Local

---

## Every Service

Must contain

- logging

- docstrings

- type hints

- exception handling

---

## Every API Endpoint

Must have

- response_model

- status_code

- dependency injection

- authentication (if required)

- validation

---

## Forbidden

No print()

No wildcard imports

No duplicated code

No circular imports

No SQL in routes

No business logic in routes

No global state