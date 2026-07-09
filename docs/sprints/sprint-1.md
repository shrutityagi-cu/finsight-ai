# Sprint 1 Plan — FinSight AI

## 1. Sprint Goal

Deliver the foundational MVP slice of FinSight AI by implementing secure authentication, a working portfolio management flow, and a local development environment that supports future market-data, news, and AI features.

## 2. User Stories

- As a new user, I want to register and sign in so that I can securely access the platform.
- As an authenticated user, I want to create and manage portfolios so that I can organize my investments.
- As an authenticated user, I want to add, edit, and remove holdings so that I can track my positions.
- As a user, I want to see a basic dashboard with portfolio summary information so that I can quickly understand my account state.
- As a developer, I want to run the application locally with Docker so that I can build and test the product efficiently.

## 3. Technical Tasks

### Backend
- Set up the FastAPI application structure using the modular monolith approach.
- Implement authentication endpoints for registration, login, and token validation.
- Create database models for users, portfolios, and holdings.
- Add Alembic migrations and database initialization scripts.
- Implement portfolio and holding CRUD APIs.
- Add basic gain/loss and performance calculations.
- Write backend unit and integration tests for authentication and portfolio flows.

### Frontend
- Initialize the Next.js application shell and shared layout.
- Build authentication screens for sign-in and sign-up.
- Build a dashboard and portfolio management screens.
- Connect the UI to the backend APIs for authentication and portfolio operations.
- Add loading, error, and empty-state handling for core flows.

### Infrastructure and Dev Experience
- Create Docker Compose configuration for the frontend, backend, and database.
- Add environment configuration templates for local development.
- Set up a basic CI workflow for linting and test execution.
- Add a simple seed dataset for local testing.

## 4. Agent Assignments

| Area | Agent | Primary Responsibility |
| --- | --- | --- |
| Product direction | Product Architect | Confirm scope, prioritize stories, and define acceptance criteria |
| Backend implementation | Backend Engineer | Authentication service, portfolio APIs, domain logic, and tests |
| Frontend implementation | Frontend Engineer | Authentication UI, dashboard, portfolio views, and API integration |
| Environment and deployment | Cloud DevOps Engineer | Docker setup, environment configuration, CI pipeline, and local runbook |
| Quality and validation | QA Engineer | Test planning, regression checks, and defect triage |

## 5. Folder Structure

```text
backend/
  app/
    api/
    core/
    models/
    schemas/
    services/
    tests/
frontend/
  src/
    app/
    components/
    lib/
    hooks/
 database/
  migrations/
 infrastructure/
  docker/
  ci/
 docs/
  sprints/
```

## 6. Deliverables

- Working authentication flow with secure login and registration.
- Backend API for portfolio and holding management.
- Initial frontend experience for sign-in, dashboard, and portfolio management.
- Local Docker-based development environment.
- Automated tests covering core backend functionality.
- Sprint 1 demo-ready build.

## 7. Acceptance Criteria

- A new user can register and log in successfully.
- An authenticated user can create, update, and delete portfolios and holdings.
- The dashboard displays portfolio summary information and a list of holdings.
- The application runs locally using Docker Compose without manual setup errors.
- Core backend tests pass and provide reasonable coverage for authentication and portfolio workflows.
- The key MVP flows are usable end-to-end from the browser.

## 8. Risks

- External market-data APIs may be delayed or rate-limited, which could slow UI enrichment.
- Authentication and authorization work can expand if security requirements are not scoped early.
- Database schema changes late in the sprint may create rework.
- Frontend and backend integration issues may delay the end-to-end demo.

### Mitigations
- Use mock or placeholder market-data responses for Sprint 1 if external APIs are not ready.
- Keep the initial scope focused on core portfolio and auth flows.
- Create and stabilize the data model early in the sprint.
- Prioritize API contracts and integration checkpoints from the start.

## 9. Timeline

### Week 1
- Day 1–2: Project scaffolding, architecture alignment, repository setup, and environment configuration.
- Day 3–4: Authentication backend, database models, and migrations.
- Day 5: Initial frontend auth flow and dashboard shell.

### Week 2
- Day 6–7: Portfolio and holding CRUD APIs and tests.
- Day 8: Frontend integration for portfolio management and dashboard data.
- Day 9: Docker Compose, CI workflow, and local runbook polish.
- Day 10: QA, bug fixing, demo preparation, and sprint review.

## 10. Recommended Implementation Order

1. Finalize sprint scope and acceptance criteria.
2. Set up the backend and frontend foundations.
3. Implement authentication and database models.
4. Build portfolio and holding API endpoints.
5. Implement the initial UI for authentication and portfolio management.
6. Connect the frontend to the backend APIs.
7. Add tests, Docker support, and CI baseline.
8. Perform QA, fix defects, and prepare the demo.

## Notes

This sprint focuses on establishing the product foundation rather than full market intelligence features. Market data, sentiment analysis, advanced ML predictions, and the AI assistant are intentionally deferred to later sprints.
