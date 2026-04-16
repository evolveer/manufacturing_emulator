# Pharma Batch Execution Simulator

> Simulated pharma batch execution workflow covering MES order flow, step execution, audit trail, deviations, and release review in a regulated manufacturing context.

## Project Overview

The **Pharma Batch Execution Simulator** is a lightweight, interactive application designed to demonstrate the core principles of pharmaceutical manufacturing execution systems (MES) and electronic batch records (EBR). 

Rather than a full production system, it serves as a conceptual bridge between business processes, regulatory requirements, and technical implementation. It proves an understanding of how manufacturing data flows from order creation to final product release.

## Why This Matters in Regulated Manufacturing

In a GxP environment, manufacturing software is not just about recording data; it is about enforcing control, ensuring traceability, and managing exceptions. This simulator highlights critical regulated-system thinking:
* **Batch Lifecycle Thinking:** Managing states across orders, batches, steps, and deviations.
* **Auditability:** Every critical action is immutably logged with timestamps, users, and before/after values.
* **Exception Management:** Out-of-spec parameters or skipped steps automatically trigger deviations that block release until justified.
* **Data-Driven Visibility:** Providing operational dashboards that aggregate complex production data into actionable insights.

## Business Scenario

The application simulates the following core workflow:
1. **ERP Order Creation:** A production planner creates a simulated order for a pharmaceutical product lot.
2. **MES Batch Instantiation:** The MES receives the order and creates a batch based on a predefined master recipe.
3. **Step Execution:** Operators execute recipe steps in sequence, capturing critical process parameters (e.g., temperature, pH, weights).
4. **Deviation Handling:** If a parameter falls outside the defined specification, or a mandatory step is skipped, the system automatically opens a deviation.
5. **Audit Trail:** The system continuously records an immutable audit trail of all actions.
6. **Review & Release:** Quality Assurance (QA) reviews the completed batch record. The system computes a disposition recommendation based on completeness and open deviations.

## Features

* **Interactive Dashboard:** Real-time metrics on active batches, deviations, and recent audit events.
* **Order Management:** Create and dispatch production orders.
* **Guided Batch Execution:** Step-by-step parameter entry with real-time validation against recipe limits.
* **Automated Deviations:** Out-of-spec entries trigger deviations requiring justification and closure.
* **Comprehensive Audit Trail:** Filterable view of all system events.
* **Automated Review Logic:** Completeness scoring and disposition recommendations (Release, Release with Comments, Reject/Hold).
* **Pre-built Scenarios:** Includes seed data for a clean batch, a batch with a minor deviation, and a batch with a critical hold.

## Demo Scenarios

The simulator comes pre-seeded with three demonstration scenarios to quickly showcase system capabilities:

* **Scenario A: Clean Batch**
  * All steps completed successfully.
  * All parameters within range.
  * No deviations.
  * Recommended Disposition: **Release**

* **Scenario B: Minor Deviation**
  * One parameter (e.g., temperature) slightly out of range.
  * Deviation opened, investigated, and closed with justification.
  * Recommended Disposition: **Release with Comments**

* **Scenario C: Critical Hold**
  * A mandatory step (e.g., sterile filtration) was skipped.
  * Critical deviation remains open.
  * Recommended Disposition: **Reject / Hold**

## Architecture

The application is built using a modern, lightweight Python stack:
* **Presentation Layer:** Streamlit for a fast, interactive, and data-rich user interface.
* **Domain Layer:** Pydantic models for robust data validation and clear entity definitions.
* **Service Layer:** Modular Python services encapsulating business logic (orders, batches, executions, deviations, review, audit).
* **Data Layer:** Simple JSON-based persistence for portability and easy reset during demonstrations.

## How to Run

### Prerequisites
* Python 3.10+
* Git

### Setup & Execution
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd manufacturing_emulator/pharma
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run the Streamlit application:
   ```bash
   streamlit run app/main.py
   ```
4. Open your browser to `http://localhost:8501`.

## Known Limitations

This project is intentionally simplified for educational and demonstration purposes. It is **not** suitable for production use.
* **Not GMP Validated:** This software has not undergone computer system validation (CSV).
* **No 21 CFR Part 11 Compliance:** It lacks real electronic signatures, secure password policies, and biometric authentication.
* **Simplified Security Model:** Role-based access control (RBAC) is simulated via simple text inputs rather than a robust identity provider.
* **No Real Integrations:** ERP and equipment connectivity are simulated; there are no actual API calls to external systems like SAP or physical PLCs.
* **Basic Persistence:** Uses JSON files instead of a relational database for ease of setup.

## Where This Applies in Real Projects

This simulator serves as a practical discussion tool for:
* MES design and requirement gathering workshops.
* Demonstrating the value of digital batch records over paper-based systems.
* Training stakeholders on exception management and review-by-exception (RBE) concepts.
* Validating digital manufacturing workflows before full-scale implementation.
