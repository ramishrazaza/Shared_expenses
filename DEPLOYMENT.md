# DEPLOYMENT.md: Deployment Guide

This guide outlines the deployment steps for the Shared Expenses App (ShareLedger) with a React frontend, Django REST API backend, and Neon PostgreSQL database.

---

## 1. Database Setup (Neon PostgreSQL)

1. Create a free account at [Neon.tech](https://neon.tech/).
2. Create a new project and select **PostgreSQL 16+**.
3. Create a database named `shared_expenses`.
4. Copy the connection string:
   `postgresql://[user]:[password]@[host]/shared_expenses?sslmode=require`

---

## 2. Backend Deployment (Render)

1. Sign up/Log in at [Render.com](https://render.com/).
2. Click **New** -> **Web Service**.
3. Link your GitHub repository.
4. Set the following configuration values:
   * **Name**: `shared-expenses-backend`
   * **Environment**: `Python`
   * **Root Directory**: `backend`
   * **Build Command**: `pip install -r requirements.txt && python manage.py migrate && python manage.py seed_data`
   * **Start Command**: `gunicorn config.wsgi:application`
5. In the **Environment Variables** section, add the following variables:
   * `DATABASE_URL` = `postgresql://[user]:[password]@[host]/shared_expenses?sslmode=require`
   * `SECRET_KEY` = `[a-random-secure-django-secret-key]`
   * `DEBUG` = `False`
   * `ALLOWED_HOSTS` = `shared-expenses-backend.onrender.com` (use your actual Render subdomain)
6. Click **Deploy Web Service**.

---

## 3. Frontend Deployment (Vercel)

1. Log in to your [Vercel](https://vercel.com/) dashboard.
2. Click **Add New** -> **Project**.
3. Import your GitHub repository.
4. Set the following configuration values:
   * **Framework Preset**: `Vite`
   * **Root Directory**: `frontend`
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
5. Click **Deploy**. Vercel will generate your live production URL (e.g. `shared-expenses-app.vercel.app`).
6. Update your Django backend `CORS_ALLOWED_ORIGINS` settings or keep `CORS_ALLOW_ALL_ORIGINS = True` to allow communication from Vercel to your Render service.

---

## 4. Production Checklist

* [ ] Disable Django debug mode (`DEBUG=False`).
* [ ] Verify that gunicorn is serving traffic.
* [ ] Apply database migrations cleanly on Neon PostgreSQL.
* [ ] Verify CORS headers allow requests from Vercel to Render.
* [ ] Verify JWT Auth tokens are stored correctly in browser localStorage.
* [ ] Run seed data to verify initial flatmates are created.
