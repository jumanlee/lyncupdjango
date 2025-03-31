# LyncUp

**LyncUp** is a full-stack web app built with Django, React, PostgreSQL, Redis, Celery, and Docker.  
It connects users in small social chat groups based on simple liking behaviour and helps simulate spontaneous social interactions.

Note the frontend side of the app is here: https://github.com/jumanlee/lyncupreact/tree/master
---

## Pre-requisite
Please have Docker Desktop ready in the background.

## Step 1: Create a `.env` File (Required)

You **must** create a `.env` file in the root of your project before running anything.  
This file holds your environment variables and is ignored by Git.

Here’s a sample `.env` you can copy and fill with your own credentials:

```env
DB_NAME=lyncup
DB_USER=myuser
DB_PASSWORD=mysecretpassword
DB_HOST=localhost
DB_PORT=5432

SECRET_KEY='django-insecure-123dummy_secret_key_here456'
```

## Step 2: Start the Project with Docker

To start the full backend app stack, run:
```
docker-compose up
```
This will:

- Build the Django image.

- Run migrations once using the migrate service.

- Start the ASGI server via Daphne (daphne -b 0.0.0.0 -p 8080 lyncup.asgi:application).

- Launch Django, PostgreSQL, Redis, Celery worker, and Celery Beat.

- Automatically attempt to load fixtures from lyncup/fixtures/initial_data.json for development/testing (can be manually removed or commented out to avoid data overwrite, see caution in .yml file).

## Step 3: If you wish to stop Django app temporarily (containers still exist):
```
docker-compose stop
```

## Step 4: If you want to start Django app after stopping:
```
docker-compose start
```
## Step 5: If you wish to tear everything down (deletes containers and data unless volumes are persisted):
```
docker-compose down
```
