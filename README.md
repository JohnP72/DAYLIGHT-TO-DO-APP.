# Daylight — your personal To-Do app

A React frontend, Python FastAPI backend, and MySQL 8.4 database.

## Deploy publicly with Railway

The public site lets visitors read all tasks and notes. Only the owner can add, edit, complete, reorder, or delete. Do not put private information in public tasks.

1. Upload the **contents** of this folder to your GitHub repository, preserving `backend` and `frontend` folders. `Dockerfile` and `railway.json` must be at the repository root. Upload the extracted files, not the ZIP. Skip `node_modules`, `dist`, and Python cache folders.
2. In Railway, create a project from that GitHub repository.
3. Add a **MySQL** database service in the same Railway project.
4. On the app service, add these variables:
   - `DATABASE_URL`: `${{MySQL.MYSQL_URL}}` (a reference to the MySQL service's private URL; if its name differs, use that name).
   - `OWNER_PASSWORD`: choose a unique password of at least 20 ASCII characters. Enter it directly into Railway, never in GitHub or chat. A password manager can generate it.
5. Deploy the app. It builds React and runs FastAPI in one service. The app listens on Railway's `PORT` automatically and creates its database tables at startup.
6. After the deployment is healthy, open the app service's **Settings → Networking → Generate Domain**. Share its HTTPS address.
7. On your new site, choose **Owner sign in** and enter the same owner password to manage tasks.

A missing or too-short owner password leaves editing locked. Signing out or refreshing the page clears the owner's sign-in from browser memory. No password is saved in browser storage. Use the generated HTTPS address for sign-in. There is one owner, not separate accounts for visitors. Incorrect sign-ins are limited to 10 attempts per minute per server-visible client address; this limit is held in memory, so keep one app replica for this simple deployment.

Railway hosts MySQL separately; it does not use the local `compose.yaml`. Railway charges depend on your plan and usage. The old ZIP in the repository can remain as an archive; the extracted files control deployment.

Official guides: [FastAPI](https://docs.railway.com/guides/fastapi), [MySQL](https://docs.railway.com/databases/mysql), [public addresses](https://docs.railway.com/networking/public-networking).

## Start locally (Windows)

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Follow its installer, including any WSL or restart instructions, and open Docker Desktop. Wait until its engine is running. Use Linux containers (the default).
2. Open this `todo-app` folder in File Explorer.
3. Create a file named `.env` in this folder containing `OWNER_PASSWORD=your-unique-password` (at least 20 ASCII characters). Keep this file private. Then double-click **Start App.cmd**. The first run downloads and builds the app and can take several minutes. Keep the window open until it finishes.
4. Your browser opens at **http://localhost:8080**. Bookmark it.

Docker runs Python, React, and MySQL together; you do not need to install those separately. Internet access is needed for the initial download/build. Visitors have read-only access. Use Owner sign in to manage tasks.

**Stop:** double-click **Stop App.cmd**. Your tasks remain in the MySQL volume. Closing your browser also keeps your tasks. Start the app again with **Start App.cmd**.

## How to use it

Sign in as the owner to use the editing controls below. Visitors can switch lists, filter tasks, and read descriptions.

- **Lists:** enter a name in the sidebar and press `+`. Use Rename list or Delete list for the selected list. Deleting a list deletes its tasks after confirmation.
- **Add tasks:** type in the main input and press Enter or Add task.
- **Complete/uncomplete:** click a task's checkbox.
- **Filter:** use All tasks, Active tasks, or Completed.
- **Description tab:** click a task's title or pencil to open its description. Edit the title and notes, choose a different list, or change completion, then click Save changes. Clear the notes and save to remove them.
- **Reorder:** select All tasks, then drag a row or use its up/down arrows. Arrows also work on phones and with a keyboard.
- **Delete tasks:** click the `×` at the right of a row and confirm.

Task creation, checkboxes, ordering, and deletion save immediately. Description changes save when you click **Save changes**.

## If it does not start

- Make sure Docker Desktop is open and its engine is running.
- If Windows asks for WSL, follow the linked Docker installation guide, then restart if requested.
- If port 8080 is already in use, stop the other app and try again.
- To see an error, open a terminal in this folder and run `docker compose logs --tail=80 app db`.
- To start manually: `docker compose up --build -d --wait`.
- To stop manually: `docker compose stop`.
- Do not run `docker compose down -v`: `-v` deletes your database volume and tasks.

## For learning and development

```
backend/main.py          API routes and database models
backend/test_app.py      API lifecycle and validation tests
frontend/src/main.jsx    React interface and interactions
frontend/src/style.css   Responsive styling
compose.yaml             MySQL and app startup configuration
Dockerfile               Builds React and serves it through FastAPI
```

API documentation is available at http://localhost:8080/docs while the app is running. The database tables are created automatically on first startup. The default list is “My tasks.”

For frontend development, install Node.js 22, open `frontend`, run `npm install`, then `npm run dev`. Its development server forwards API requests to FastAPI on port 8000. For backend development, install Python 3.12, install `backend/requirements.txt` in a virtual environment, set `DATABASE_URL` to your MySQL connection URL, then run `uvicorn main:app --reload` from `backend`.

This version has one owner and public viewing. The supplied Compose database credentials are only for local development. Railway supplies separate database credentials. Never commit real passwords or a `.env` file.

## Verification and local preview

The API tests use an isolated SQLite database so they can run without MySQL: install `pytest` and `httpx`, then run `python -m pytest -q` from `backend`.

The preview prepared in this Codex session uses a separate SQLite database under `work`; it does not write to the MySQL database. Starting with Docker creates your actual MySQL workspace. Preview tasks are not automatically transferred. Docker/MySQL startup requires Docker Desktop and has not been exercised on this computer.

No other decisions are required for this version. Due dates, reminders, and accounts can be added later if you need them.

