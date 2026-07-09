# Watchlist module implementation TODO (Agent 5)

- [ ] Inspect current watchlist models/schemas/services/routes for missing methods and correctness.
- [x] Update `backend/app/schemas/watchlist.py` to include required schema classes.
- [x] Update `backend/app/services/watchlist_service.py` to implement the required WatchlistService methods with:
  - [x] Async SQLAlchemy usage
  - [x] Ownership checks (`watchlist.user_id == current_user.id`)
  - [x] Soft delete for watchlists when supported
  - [x] 404 when missing, 403/409 where required
  - [x] Duplicate symbol prevention within a watchlist (HTTP 409)
- [x] Update `backend/app/api/v1/routes/watchlists.py` to expose required endpoints and correct route paths:
  - [x] GET /watchlists
  - [x] GET /watchlists/{id}
  - [x] POST /watchlists
  - [x] PATCH /watchlists/{id}
  - [x] DELETE /watchlists/{id}
  - [x] GET /watchlists/{id}/items
  - [x] POST /watchlists/{id}/items
  - [x] DELETE /watchlist-items/{id}
- [x] Ensure only watchlist module files are modified; do not touch auth or other APIs.
- [ ] Run `python -m compileall` for modified files.

