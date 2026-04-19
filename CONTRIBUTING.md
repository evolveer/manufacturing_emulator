# Contributing to Manufacturing Emulator

Thank you for your interest in contributing to the Manufacturing Emulator project! This document provides guidelines and instructions for contributing to the repository.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Project Structure](#project-structure)
5. [Coding Standards](#coding-standards)
6. [Testing](#testing)
7. [Pull Request Process](#pull-request-process)

## Project Overview

The Manufacturing Emulator is a comprehensive system that simulates a complete manufacturing environment, including:
- **ERP (Enterprise Resource Planning)**: Manages orders, products, and shipments.
- **MES (Manufacturing Execution System)**: Handles work orders, machines, scheduling, and quality checks.
- **PCS (Process Control System)**: Simulates machine operations, parameters, cycles, and alarms.
- **Pharma App**: A Streamlit-based application for pharmaceutical batch simulation and orchestration.

The system uses Python (Flask, Streamlit), JavaScript (vanilla), and SQLite databases.

## Getting Started

To set up the project locally for development:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/evolveer/manufacturing_emulator.git
   cd manufacturing_emulator
   ```

2. **Set up the Python environment**:
   It is recommended to use a virtual environment.
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. **Initialize the databases**:
   Run the initialization script to create all required tables and seed demo data.
   ```bash
   python database/init_db.py
   ```

4. **Start the services**:
   You can start all microservices using the provided script.
   ```bash
   ./start.sh
   ```
   Alternatively, start them individually:
   - ERP: `python erp/api.py` (Port 5001)
   - MES: `python mes/api.py` (Port 5002)
   - PCS: `python pcs/api.py` (Port 5003)
   - Interface: `python common/interface.py` (Port 5000)
   - Pharma App: `streamlit run pharma/app/main.py` (Port 8501)

## Development Workflow

1. **Create a branch**:
   Always create a new branch for your feature or bug fix.
   ```bash
   git checkout -b feature/your-feature-name
   ```
   Or for a bug fix:
   ```bash
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**:
   Ensure your code follows the project's coding standards.

3. **Test your changes**:
   Verify that your changes do not break existing functionality. Run relevant tests if available.

4. **Commit your changes**:
   Write clear and descriptive commit messages.
   ```bash
   git commit -m "feat: add new feature description"
   ```
   We recommend following [Conventional Commits](https://www.conventionalcommits.org/).

5. **Push and create a Pull Request**:
   Push your branch to GitHub and open a Pull Request against the `main` branch.

## Project Structure

The project is organized into several key directories:

- `common/`: Contains the main interface proxy (`interface.py`) and shared frontend templates/static files.
- `database/`: Contains SQLite database files (`erp.db`, `mes.db`, `pcs.db`) and the `init_db.py` script.
- `erp/`: Enterprise Resource Planning microservice.
- `mes/`: Manufacturing Execution System microservice.
- `pcs/`: Process Control System microservice.
- `pharma/`: Streamlit application for pharma batch simulation.
- `reports/`: Generated automated reports.
- `tests/`: Project test suite.

## Coding Standards

- **Python**: Follow [PEP 8](https://peps.python.org/pep-0008/) style guide. Use descriptive variable and function names.
- **JavaScript**: Write clean, vanilla JavaScript. Avoid unnecessary dependencies.
- **HTML/CSS**: Use Bootstrap 5 for styling. Ensure responsive design.
- **Documentation**: Update docstrings and inline comments for any new or modified complex logic.

## Testing

Before submitting a Pull Request, ensure that:
- All microservices start correctly without errors.
- The databases initialize properly using `init_db.py`.
- The dashboards (Main, ERP, MES, PCS) load and display data correctly.
- Any new features are thoroughly tested manually or with automated tests in the `tests/` directory.

## Pull Request Process

1. Ensure your PR description clearly describes the problem and solution.
2. Link any relevant issues in the PR description (e.g., "Fixes #123").
3. Your PR will be reviewed by maintainers. Please be responsive to feedback and make necessary adjustments.
4. Once approved, a maintainer will merge your PR.

Thank you for contributing!
