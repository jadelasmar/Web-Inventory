# Repository Guidelines

## Project Recap (Read First)
- **Purpose:** BIM POS Inventory is a Streamlit-based inventory system with role-based access, product catalog, stock movements, alerts, and basic analytics.
- **Entry point:** `app.py` wires authentication, DB init, sidebar navigation, and routes to page renderers.
- **Routing:** Sidebar labels map to `page_modules/*.py` `render(conn)` functions; admin-only pages are gated by `st.session_state.admin_mode`.
- **Menu labels:** Centralized in `core/constants.py` (MENU_* constants) and reused by `app.py` and `ui/sidebar.py`.
- **Data access:** All database logic lives in `core/services.py`; pages should call services instead of writing SQL.
- **Database selection:** `core/db_init.py` uses PostgreSQL when `.streamlit/secrets.toml` has `[postgres]`; otherwise SQLite at `data/bimpos_inventory.db` (ensures `data/` exists).
- **Schema:** `services.init_db` creates/migrates:
  - `products` (name, category, brand, description, image_url, current_stock, cost_price, sale_price, supplier, isactive)
  - `movements` (product_name, movement_type, quantity, price, supplier_customer, notes, movement_date)
  - `users` (username, password_hash, name, role, status, created_at, approved_by)
  - `parties` (name, party_type, isactive, created_at)
- **Stock logic:** `record_movement` updates `products.current_stock` and inserts a movement; `ADJUSTMENT` supports positive or negative quantities. `delete_movement` reverses the stock effect.
- **Initial stock:** Admins can record/edit a single INITIAL STOCK entry via the Stock Movement page; it sets `current_stock` to the entered quantity and is only allowed if there are no other movements.
- **Soft delete:** `delete_product` sets `products.isactive=0` and hides products; `restore_product` reactivates them.
- **Auth flow:** `core/simple_auth.py` supports:
  - bootstrap owner/admin users from secrets.toml
  - signup creates `users` row with `pending` status
  - admin/owner approve in User Management
  - 30-day auto-login persisted in `.streamlit/user_session.json`
- **Caching:** `get_products` and `get_movements` use `st.cache_data`; cache invalidated via `products_cache_version` / `movements_cache_version` in session state.
- **Images:** Local product images live in `assets/product_images/` and are auto-resolved by product name; renames attempt to rename local files.
- **Encoding:** UI emoji are represented with Unicode escape sequences in code to avoid encoding issues on Windows consoles.
- **Parties:** New parties are auto-added from Stock Movement. Admins manage/rename/delete in the Customers & Suppliers page.
- **UI components:** Uses `streamlit-free-text-select` for single-field select-or-create inputs (party, brand, category, product).

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

## Future Ideas (Backlog)
- Bulk physical inventory adjust (upload Name/SKU + Stock and log adjustments).
- Add SKU/Barcode field and allow lookup/import by SKU.
- Local network deployment: static IP/DNS name for LAN access + mobile access on same Wi-Fi.
