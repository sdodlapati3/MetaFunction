# MetaFunction Development Makefile

.PHONY: help install install-dev test lint format clean run docker-build docker-run

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ -v --cov=app --cov=resolvers --cov-report=html

lint: ## Run linting
	flake8 app/ resolvers/ tests/
	mypy app/ resolvers/

format: ## Format code
	black app/ resolvers/ tests/

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/

run: ## Run the application in development mode
	FLASK_ENV=development flask run --host=0.0.0.0 --port=8000 --debug

docker-build: ## Build Docker image
	docker build -t metafunction .

docker-run: ## Run Docker container
	docker run -p 8000:8000 --env-file .env metafunction

migrate: ## Run data migration
	python scripts/migrate_data.py

benchmark: ## Run performance benchmarks
	python scripts/benchmark_resolvers.py
