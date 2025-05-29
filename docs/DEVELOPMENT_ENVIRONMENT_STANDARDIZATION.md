# Development Environment Standardization

## Overview
A comprehensive standardization system that ensures consistent development environments across all team members, reducing "works on my machine" issues and accelerating onboarding.

## Core Components

### 1. **Containerized Development Environment**
```dockerfile
# .devcontainer/Dockerfile
FROM python:3.11-slim

# Development tools and dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    vim \
    htop \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python environment setup
COPY requirements*.txt ./
RUN pip install -r requirements.txt \
    && pip install -r requirements-dev.txt

# VS Code extensions and settings
COPY .devcontainer/settings.json /tmp/vscode-settings.json
COPY .devcontainer/extensions.json /tmp/vscode-extensions.json

# Development user setup
RUN useradd -m -s /bin/bash developer
USER developer
WORKDIR /workspace

# Pre-commit hooks setup
RUN git config --global init.defaultBranch main
COPY .pre-commit-config.yaml ./
RUN pre-commit install
```

### 2. **Automated Environment Setup**
```bash
#!/bin/bash
# scripts/setup-dev-environment.sh

set -e

echo "🚀 Setting up MetaFunction Development Environment"

# Check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Please install Docker first."
        exit 1
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        echo "❌ Git not found. Please install Git first."
        exit 1
    fi
    
    echo "✅ Prerequisites check passed"
}

# Setup development container
setup_container() {
    echo "🐳 Setting up development container..."
    
    docker-compose -f .devcontainer/docker-compose.yml up -d
    docker-compose -f .devcontainer/docker-compose.yml exec app bash -c "
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        pre-commit install
        python -m pytest tests/ --collect-only
    "
    
    echo "✅ Development container ready"
}

# Install development tools
install_tools() {
    echo "🛠️ Installing development tools..."
    
    # Install recommended VS Code extensions
    if command -v code &> /dev/null; then
        code --install-extension ms-python.python
        code --install-extension ms-python.black-formatter
        code --install-extension ms-python.flake8
        code --install-extension ms-python.isort
        code --install-extension GitHub.copilot
        echo "✅ VS Code extensions installed"
    fi
    
    # Setup git hooks
    cp scripts/git-hooks/* .git/hooks/
    chmod +x .git/hooks/*
    echo "✅ Git hooks installed"
}

# Validate setup
validate_setup() {
    echo "🧪 Validating setup..."
    
    # Test Python environment
    python -c "
import sys
import pkg_resources
required = ['flask', 'pytest', 'black', 'flake8']
installed = [pkg.project_name for pkg in pkg_resources.working_set]
missing = [pkg for pkg in required if pkg not in installed]
if missing:
    print(f'❌ Missing packages: {missing}')
    sys.exit(1)
else:
    print('✅ All required packages installed')
"

    # Test application startup
    timeout 10s python app.py &
    sleep 5
    if curl -f http://localhost:8000/health &> /dev/null; then
        echo "✅ Application starts successfully"
    else
        echo "⚠️ Application startup test failed (check manually)"
    fi
    
    # Cleanup test process
    pkill -f "python app.py" || true
}

# Main execution
main() {
    check_prerequisites
    setup_container
    install_tools
    validate_setup
    
    echo ""
    echo "🎉 Development environment setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Open VS Code: 'code .'"
    echo "2. Start development server: 'python app.py'"
    echo "3. Run tests: 'pytest tests/'"
    echo "4. Check code quality: 'pre-commit run --all-files'"
}

main "$@"
```

### 3. **Pre-commit Quality Gates**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ['--maxkb=1000']

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=88', '--extend-ignore=E203,W503']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-r', '.', '-f', 'json', '-o', 'bandit-report.json']

  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest tests/ --collect-only
        language: system
        pass_filenames: false
        always_run: true
```

### 4. **Standardized VS Code Configuration**
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.linting.banditEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": ["tests/"],
    
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "editor.rulers": [88],
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true,
    
    "git.enableCommitSigning": true,
    "git.autofetch": true,
    
    "extensions.ignoreRecommendations": false,
    "workbench.colorTheme": "Default Dark+",
    "terminal.integrated.defaultProfile.linux": "bash"
}
```

```json
// .vscode/extensions.json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.black-formatter",
        "ms-python.flake8",
        "ms-python.isort",
        "ms-python.mypy",
        "GitHub.copilot",
        "GitHub.vscode-pull-request-github",
        "ms-vscode.test-adapter-converter",
        "redhat.vscode-yaml",
        "ms-vscode.vscode-json",
        "eamodio.gitlens",
        "ms-vsliveshare.vsliveshare",
        "streetsidesoftware.code-spell-checker"
    ]
}
```

### 5. **Environment Validation Script**
```python
#!/usr/bin/env python3
# scripts/validate_environment.py

import sys
import subprocess
import pkg_resources
import importlib
import json
from pathlib import Path
from typing import List, Dict, Any

class EnvironmentValidator:
    def __init__(self):
        self.results = {
            'python_version': self.check_python_version(),
            'required_packages': self.check_required_packages(),
            'development_tools': self.check_development_tools(),
            'git_configuration': self.check_git_configuration(),
            'pre_commit_hooks': self.check_pre_commit_hooks(),
            'application_startup': self.check_application_startup(),
            'test_execution': self.check_test_execution()
        }
    
    def check_python_version(self) -> Dict[str, Any]:
        """Validate Python version meets requirements"""
        version = sys.version_info
        required_major, required_minor = 3, 8
        
        is_valid = version.major >= required_major and version.minor >= required_minor
        
        return {
            'status': 'PASS' if is_valid else 'FAIL',
            'current': f"{version.major}.{version.minor}.{version.micro}",
            'required': f"{required_major}.{required_minor}+",
            'message': f"Python {version.major}.{version.minor} {'meets' if is_valid else 'does not meet'} requirements"
        }
    
    def check_required_packages(self) -> Dict[str, Any]:
        """Check if all required packages are installed"""
        required_packages = [
            'flask', 'requests', 'pytest', 'black', 'flake8', 
            'mypy', 'isort', 'bandit', 'pre-commit'
        ]
        
        installed = {pkg.project_name.lower() for pkg in pkg_resources.working_set}
        missing = [pkg for pkg in required_packages if pkg.lower() not in installed]
        
        return {
            'status': 'PASS' if not missing else 'FAIL',
            'installed': list(installed),
            'missing': missing,
            'message': f"{'All packages installed' if not missing else f'Missing: {missing}'}"
        }
    
    def check_development_tools(self) -> Dict[str, Any]:
        """Check development tools availability"""
        tools = {
            'git': 'git --version',
            'docker': 'docker --version',
            'pre-commit': 'pre-commit --version'
        }
        
        tool_status = {}
        for tool, command in tools.items():
            try:
                result = subprocess.run(command.split(), capture_output=True, text=True)
                tool_status[tool] = {
                    'available': result.returncode == 0,
                    'version': result.stdout.strip() if result.returncode == 0 else None
                }
            except FileNotFoundError:
                tool_status[tool] = {'available': False, 'version': None}
        
        all_available = all(status['available'] for status in tool_status.values())
        
        return {
            'status': 'PASS' if all_available else 'WARN',
            'tools': tool_status,
            'message': 'All development tools available' if all_available else 'Some tools missing'
        }
    
    def check_git_configuration(self) -> Dict[str, Any]:
        """Validate git configuration"""
        try:
            name = subprocess.run(['git', 'config', 'user.name'], capture_output=True, text=True)
            email = subprocess.run(['git', 'config', 'user.email'], capture_output=True, text=True)
            
            has_config = name.returncode == 0 and email.returncode == 0
            
            return {
                'status': 'PASS' if has_config else 'WARN',
                'user_name': name.stdout.strip() if has_config else None,
                'user_email': email.stdout.strip() if has_config else None,
                'message': 'Git configured' if has_config else 'Git user configuration missing'
            }
        except Exception:
            return {
                'status': 'FAIL',
                'message': 'Unable to check git configuration'
            }
    
    def check_pre_commit_hooks(self) -> Dict[str, Any]:
        """Check if pre-commit hooks are installed"""
        hooks_dir = Path('.git/hooks')
        pre_commit_hook = hooks_dir / 'pre-commit'
        
        return {
            'status': 'PASS' if pre_commit_hook.exists() else 'WARN',
            'installed': pre_commit_hook.exists(),
            'message': 'Pre-commit hooks installed' if pre_commit_hook.exists() else 'Pre-commit hooks not installed'
        }
    
    def check_application_startup(self) -> Dict[str, Any]:
        """Test if application can start without errors"""
        try:
            # Import test - check if main modules can be imported
            import app.main
            return {
                'status': 'PASS',
                'message': 'Application imports successfully'
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'error': str(e),
                'message': f'Application import failed: {e}'
            }
    
    def check_test_execution(self) -> Dict[str, Any]:
        """Test if pytest can discover and collect tests"""
        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', 'tests/', '--collect-only', '-q'],
                capture_output=True, text=True, timeout=30
            )
            
            return {
                'status': 'PASS' if result.returncode == 0 else 'WARN',
                'tests_collected': result.returncode == 0,
                'output': result.stdout if result.returncode == 0 else result.stderr,
                'message': 'Tests collected successfully' if result.returncode == 0 else 'Test collection failed'
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'error': str(e),
                'message': f'Test execution check failed: {e}'
            }
    
    def generate_report(self) -> str:
        """Generate a comprehensive validation report"""
        report = ["🔍 MetaFunction Development Environment Validation Report", "=" * 60, ""]
        
        overall_status = "PASS"
        for check_name, result in self.results.items():
            status_emoji = {
                'PASS': '✅',
                'WARN': '⚠️',
                'FAIL': '❌'
            }.get(result['status'], '❓')
            
            report.append(f"{status_emoji} {check_name.replace('_', ' ').title()}: {result['status']}")
            report.append(f"   {result['message']}")
            
            if result['status'] == 'FAIL':
                overall_status = 'FAIL'
            elif result['status'] == 'WARN' and overall_status != 'FAIL':
                overall_status = 'WARN'
            
            report.append("")
        
        report.extend([
            "=" * 60,
            f"Overall Status: {overall_status}",
            "",
            "Recommendations:",
        ])
        
        if overall_status != 'PASS':
            recommendations = self.generate_recommendations()
            report.extend([f"  • {rec}" for rec in recommendations])
        else:
            report.append("  ✅ Environment is properly configured!")
        
        return "\n".join(report)
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        for check_name, result in self.results.items():
            if result['status'] in ['FAIL', 'WARN']:
                if check_name == 'python_version':
                    recommendations.append("Upgrade Python to version 3.8 or higher")
                elif check_name == 'required_packages':
                    recommendations.append(f"Install missing packages: pip install {' '.join(result['missing'])}")
                elif check_name == 'development_tools':
                    missing_tools = [tool for tool, status in result['tools'].items() if not status['available']]
                    recommendations.append(f"Install missing development tools: {', '.join(missing_tools)}")
                elif check_name == 'git_configuration':
                    recommendations.append("Configure git: git config --global user.name 'Your Name' && git config --global user.email 'your.email@domain.com'")
                elif check_name == 'pre_commit_hooks':
                    recommendations.append("Install pre-commit hooks: pre-commit install")
                elif check_name == 'application_startup':
                    recommendations.append("Fix application import errors before proceeding")
                elif check_name == 'test_execution':
                    recommendations.append("Fix test configuration and ensure pytest can run")
        
        return recommendations
    
    def save_report(self, filename: str = 'environment_validation_report.json'):
        """Save detailed results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Detailed report saved to {filename}")

if __name__ == "__main__":
    validator = EnvironmentValidator()
    print(validator.generate_report())
    
    if len(sys.argv) > 1 and sys.argv[1] == '--save':
        validator.save_report()
```

### 6. **Makefile for Common Operations**
```makefile
# Makefile
.PHONY: help setup test lint format clean dev-env validate

help:  ## Show this help message
	@echo 'MetaFunction Development Commands:'
	@echo ''
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Set up development environment
	@echo "🚀 Setting up development environment..."
	@bash scripts/setup-dev-environment.sh

validate: ## Validate development environment
	@echo "🔍 Validating development environment..."
	@python scripts/validate_environment.py

dev-env: ## Start development environment
	@echo "🐳 Starting development environment..."
	@docker-compose -f .devcontainer/docker-compose.yml up -d

install: ## Install dependencies
	@echo "📦 Installing dependencies..."
	@pip install -r requirements.txt
	@pip install -r requirements-dev.txt

test: ## Run all tests
	@echo "🧪 Running tests..."
	@pytest tests/ -v

test-quick: ## Run quick tests only
	@echo "⚡ Running quick tests..."
	@pytest tests/unit/ -v

test-integration: ## Run integration tests
	@echo "🔗 Running integration tests..."
	@pytest tests/integration/ -v

lint: ## Run linting
	@echo "🔍 Running linters..."
	@flake8 app/ resolvers/ tests/
	@mypy app/ resolvers/
	@bandit -r app/ resolvers/

format: ## Format code
	@echo "✨ Formatting code..."
	@black app/ resolvers/ tests/
	@isort app/ resolvers/ tests/

security: ## Run security checks
	@echo "🔒 Running security checks..."
	@bandit -r app/ resolvers/ -f json -o bandit-report.json
	@safety check

pre-commit: ## Run pre-commit hooks
	@echo "🪝 Running pre-commit hooks..."
	@pre-commit run --all-files

clean: ## Clean temporary files
	@echo "🧹 Cleaning temporary files..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@rm -rf .pytest_cache/
	@rm -rf htmlcov/
	@rm -rf .coverage

run: ## Start the application
	@echo "🚀 Starting MetaFunction..."
	@python app.py

run-dev: ## Start in development mode
	@echo "🔧 Starting MetaFunction in development mode..."
	@FLASK_ENV=development python app.py

docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	@docker build -t metafunction:latest .

docker-run: ## Run Docker container
	@echo "🐳 Running Docker container..."
	@docker run -p 8000:8000 metafunction:latest

ci-local: ## Run CI pipeline locally
	@echo "🤖 Running CI pipeline locally..."
	@make lint
	@make test
	@make security
	@echo "✅ Local CI pipeline completed successfully!"
```

## Implementation Benefits

### 1. **Consistent Development Experience**
- Every developer has the same tools and configuration
- Eliminates environment-specific bugs and issues
- Faster onboarding for new team members

### 2. **Quality Assurance**
- Pre-commit hooks prevent bad code from being committed
- Automated linting and formatting maintain code standards
- Comprehensive validation ensures environment integrity

### 3. **Productivity Enhancement**
- One-command environment setup
- Automated tool configuration
- Quick access to common development tasks

### 4. **Maintainability**
- Standardized toolchain reduces maintenance overhead
- Centralized configuration management
- Easy updates and upgrades across all environments

This standardization system ensures that all developers work in consistent, properly configured environments while maintaining high code quality and development velocity.
