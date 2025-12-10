.PHONY: help install dev run test lint format migrate shell docker-up docker-down docker-logs clean

# Default target
help:
	@echo "Telegram Channels Admin - Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development:"
	@echo "  install       Install Python dependencies"
	@echo "  dev           Run development server"
	@echo "  run           Run production server (gunicorn)"
	@echo "  celery        Run Celery worker"
	@echo "  beat          Run Celery beat scheduler"
	@echo "  shell         Open Django shell"
	@echo ""
	@echo "Database:"
	@echo "  migrate       Run database migrations"
	@echo "  makemigrations Create new migrations"
	@echo "  loaddata      Load initial fixtures"
	@echo ""
	@echo "Testing:"
	@echo "  test          Run tests"
	@echo "  test-cov      Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          Run linter (ruff)"
	@echo "  format        Format code (black)"
	@echo "  typecheck     Run type checker (mypy)"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up     Start all services"
	@echo "  docker-down   Stop all services"
	@echo "  docker-logs   View logs"
	@echo "  docker-build  Build Docker images"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean         Remove cache files"

# Development
install:
	pip install -r requirements.txt

dev:
	cd backend && python manage.py runserver

run:
	cd backend && gunicorn --bind 0.0.0.0:8000 --workers 4 backend.wsgi:application

celery:
	cd backend && celery -A backend worker -l INFO

beat:
	cd backend && celery -A backend beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

shell:
	cd backend && python manage.py shell

# Database
migrate:
	cd backend && python manage.py migrate

makemigrations:
	cd backend && python manage.py makemigrations

loaddata:
	cd backend && python manage.py loaddata initial_languages

createsuperuser:
	cd backend && python manage.py createsuperuser

# Testing
test:
	cd backend && pytest

test-cov:
	cd backend && pytest --cov=apps --cov-report=html

# Code Quality
lint:
	ruff check backend/

format:
	black backend/
	ruff check --fix backend/

typecheck:
	cd backend && mypy apps/

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build

docker-migrate:
	docker-compose exec web python manage.py migrate

docker-createsuperuser:
	docker-compose exec web python manage.py createsuperuser

docker-shell:
	docker-compose exec web python manage.py shell

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".mypy_cache" -delete
	find . -type d -name "htmlcov" -delete
	find . -type f -name ".coverage" -delete

