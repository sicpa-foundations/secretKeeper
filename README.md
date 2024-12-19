# Secret Keeper

![img.png](img.png)

SecretKeeper is a tool for detecting secrets and misconfigurations on your Git repositories (Bitbucket and GitHub).
It uses [gitleaks](https://github.com/gitleaks/gitleaks) to scan for secrets, in order to reduce the number
of false positives, it has the ability to fetch the secrets in Hashicorp Vault.

The current features for BitBucket integration:

- Scan repositories for secrets
- Check repository settings (for example default branch should use a PR, no history deletion)
- Add confidentiality label on repositories ("Confidential" or "Internal" label)
- Send grouped notifications by email to share new findings

SecretKeeper **doesn't** store secrets it found, only the line number.

This project is using Celery to process tasks asynchronously.
To visualize the results from the database, you can create dashboards
with [metabase](https://github.com/metabase/metabase).

## Docker installation

We provide a docker-compose.yml file, to easily run the project.

### Configuration

There is a file in config/default.yml that allows you to configure the repositories and the vault.
You need to set the .env file with your configuration, and pass the file to your container.

When running the docker image, you can put the config file in "/config", or specify it in the GITLEAKS_CONFIG_FILE env
variable.

## Architecture

### Scheduler

Celery uses a separate docker image to run the scheduled tasks, called the Celery beat.

It can be seen in the docker-compose.local.yml file.

Create a .env file, that you can copy from the .env.example file.

Then you can run the following command:

```bash
poetry install --no-root  
export $(cat .env | xargs)
poetry run celery -A app.celery worker --concurrency=1 
```

Don't forget to have the rabbitMQ running.

### Structure

There is three different modules:

- Fetchers -> It fetches data from various source (bitbucket, github) and fill the database with it
- Processors -> It processes the data, and run gitleaks and classification on them
- Checkers -> It checks that some rules are applied (security best practices) and notify when it isn't respected

### Basic command

#### Alembic (db migration)

`alembic  -c migrations/alembic.ini revision --autogenerate` This will create a file into `migrations/versions` with
your DB schema to update  
`alembic -c migrations/alembic.ini upgrade head` This upgrade your Database schema (URI from config.py) from
the file created before

### Add a Sqlalchemy model

Simply add your file to the `models` folder (or add sub folders) then add this to the `common/models/__init__.py`
file.  
Alembic will then be aware of your new model.

## How to use it

### GitLeaks

#### Analyse a simple repo

`celery -A app call app.tasks.processors --repo-url "https://my_bitbucket/scm/project_name/repo_name.git"`

| Params        | Description                                                                                              |
|---------------|----------------------------------------------------------------------------------------------------------|
| --config-file | Scan only current branch, not all history                                                                |
| --single_repo | Is True when calling this method directly, It will clean the secrets file and the reports. default: True |

#### Analyse all the repo

`poetry run celery -A app call app.tasks.processors`

You can specify with a global variable the config file you want, for example: scan_bitbucket.yml
``

### Runners``

## Fetchers

This task will fetch the projects, repositories, permissions, settings and users' permissions and fill the database
with those data

`poetry run celery -A app call app.tasks.fetchers`

## Processors

This task will analyse the repositories for potential leaks and run the classification algorithm on each of them
`poetry run celery -A app call app.tasks.processors`

## Checkers

This task will check that all the best practices (in checkers folder) are respected and create notification if
it is not the case

`poetry run celery -A app call app.tasks.checkers`

## Notifications

This task will read all the notifications, group them and send them by email or by teams, depending on the configuration

`poetry run celery -A app call app.tasks.notifications`

## Development

## Initial setup

Clone the project, the project will use python 3.12 and poetry.

`poetry install`

This project uses Black and flake8 for code formatting and respect of the guidelines.

### How to run it locally

Running rabbitMQ

```bash
docker run --restart always -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=mypass -p 5672:5672 rabbitmq:latest
```

Then from the **root** directory

```bash
poetry run celery -A app.celery worker -l info
```

You should now have a celery worker running locally.

An alternative can be to use the docker-compose.local.yml file at the root of the project.

## How to send tasks

```bash
poetry run celery -A app.celery call app.tasks.fetchers
```
