#an pick a specific Python version like python:3.12 alternatively
FROM python:3.12

#makes Python output unbuffered (logs show up right away)
ENV PYTHONUNBUFFERED=1

#create app directory inside container
WORKDIR /usr/src/app

#copy requirements file into the container
COPY requirements.txt .

#install dependencies
RUN pip install --no-cache-dir -r requirements.txt

#copy the rest of your code
COPY . .

#Optional: If want to run migrations here or collectstatic in production,
#could add commands like:
#RUN python manage.py collectstatic --noinput

#By default, no CMD is declared here. We'll use docker-compose to set the command.
