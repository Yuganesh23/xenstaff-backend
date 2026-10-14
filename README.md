# XenStaff Backend API

Production-grade, multi-tenant B2B HRMS, attendance, and deterministic payroll SaaS engine built for Indian SMBs & MSMEs by XenFirm Technologies.

## 🚀 Key Features

- **Strict Multi-Tenancy**: Tenant data isolation at the model, queryset, and service layer with zero cross-organization leakage.
- **Deterministic Payroll Engine**: High-precision `Decimal` arithmetic, formula proration for mid-month joining, LOP deductions, overtime, and frozen state machine (`DRAFT` → `REVIEW` → `APPROVED` → `PUBLISHED` → `CLOSED`).
- **Shift & Attendance Processing**: Authoritative server clock punches, idempotency keys, overnight shifts, late arrival thresholds, and regularization approval workflows.
- **Cryptographic PDF Payslips**: Tamper-proof, cryptographically signed PDF payslips with dual-language support (English and Tamil) and Indian Rupee formatting.
- **Statutory Indian Compliance**: PF, ESI, Professional Tax, TDS/Income Tax slab calculations, and audit trail logs.
- **Subscription & Billing**: Multi-tier SaaS subscription model (Starter, Growth, Business) with Razorpay integration and automated webhook processing.
- **Enterprise Security**: Role-based access control (RBAC), secure employee invitation links with 48h expiration tokens, and password reset flows.

## 🛠 Tech Stack

- **Framework**: Django 6.1.2 & Django REST Framework (DRF)
- **Language**: Python 3.12+
- **Database**: PostgreSQL (Production) / SQLite (Development)
- **Testing**: pytest & pytest-django (100% core test suite passing)
- **PDF Generation**: ReportLab
- **Authentication**: JWT & Django Token Authentication

## 🏁 Getting Started

### 1. Prerequisites
- Python 3.12 or newer
- Virtual environment (`venv`)

### 2. Setup & Installation
```bash
# Clone the repository
git clone <your-backend-repo-url>
cd xenstaff-backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed initial system data (subscription plans, shift templates, leave types)
python manage.py seed_system

# Start development server
python manage.py runserver 0.0.0.0:8000
```

### 3. Running Tests
```bash
pytest
```

---
© 2026 XenFirm Technologies. All rights reserved.
