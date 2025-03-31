## LyncUp

**LyncUp** is a full-stack web app built with Django, React, PostgreSQL, Redis, Celery, and Docker.  
It connects users in small social chat groups based on simple liking behaviour and helps simulate spontaneous social interactions.


## LyncUp's frontend React app's codebase is here: 
https://github.com/jumanlee/lyncupreact

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

## Step 3: Load all initial data
```
docker-compose exec django python manage.py loaddata lyncup/fixtures/initial_data.json
```
Once the data is loaded, go to Django admin, click "Periodic tasks" on the left panel, and double check that Build Clusters and Annoy AND Run Matching Algo have both been set to "Enabled". Build Clusters and Annoy is especially crucial as it creates the Annoy files that the matching algorithm relies on to match users. Run Matching Algo runs the matching algorithm periodically.

## If you wish to stop Django app temporarily (containers still exist):
```
docker-compose stop
```

## If you want to start Django app after stopping:
```
docker-compose start
```
## If you wish to tear everything down (deletes containers and data unless volumes are persisted):
```
docker-compose down
```
