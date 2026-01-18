# Repository Guidelines

## Project Structure
- `app.py` is the Streamlit entry point.
- `core/` holds core logic (auth, DB init, services, constants).
- `page_modules/` contains Streamlit pages (dashboard, inventory, movements, alerts, user management).
- `ui/` provides shared UI components and navigation.
- `utils/` has small scripts (e.g., `generate_password_hash.py`).
- `assets/` stores static assets such as `assets/product_images/`.
- `data/` is used for local SQLite data files.
- `.streamlit/` contains Streamlit config; `secrets.toml` is local-only.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` installs Python dependencies.
- `streamlit run app.py` runs the app locally (SQLite fallback by default).
- `python utils/generate_password_hash.py` generates a password hash for owner/admin setup.

## Coding Style & Naming Conventions
- Use 4-space indentation and follow existing Python/Streamlit patterns.
- Prefer `snake_case` for functions and variables, `UPPER_SNAKE_CASE` for constants.
- Keep page modules focused on UI flow; keep database logic in `core/services.py`.

## Testing Guidelines
- No automated test suite is present in this repo.
- If adding tests, keep them small and executable locally; propose a `tests/` directory and name tests like `test_inventory.py`.
- Manually verify key flows (login, inventory CRUD, movement log, alerts) before PRs.

## Commit & Pull Request Guidelines
- Commit history favors short, imperative summaries (e.g., `fix image name`, `enable renaming`).
- Keep commits scoped to one change; avoid bundling data or asset bulk updates with logic changes.
- PRs should include: a clear description, linked issue (if any), and screenshots/GIFs for UI changes.

## Configuration & Secrets
- Local secrets live in `.streamlit/secrets.toml` and should not be committed.
- PostgreSQL is used in production; SQLite is the default for local development.
