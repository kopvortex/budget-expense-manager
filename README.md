# Budget Manager - Django Application

A comprehensive budget management application built with Django that helps you track income, expenses, manage bank accounts, set budgets, and generate financial reports.

![Budget Manager](https://img.shields.io/badge/Django-4.2.9-green.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-blue.svg)

---

## 📑 Table of Contents
- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Quick Start](#-quick-start)
  - [Docker Deployment](#docker-deployment)
  - [Kubernetes/Helm Deployment](#kuberneteshelm-deployment)
  - [Manual Installation](#manual-installation)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [Project Structure](#-project-structure)
- [Security](#-security)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## ✨ Features

### 💰 Financial Tracking
- **Income Management**: Track all your income sources with categories
- **Expense Management**: Monitor your spending across different categories
- **Bank Accounts**: Manage multiple bank accounts (savings, checking, credit cards, cash, investments)
- **Transfers**: Transfer funds between accounts with automatic balance updates

### 📊 Budgeting & Reports
- **Monthly Budgets**: Set budget limits for expense categories
- **Budget Tracking**: Real-time tracking of budget usage with visual indicators
- **Monthly Summary**: Detailed monthly financial reports with charts
- **Annual Summary**: Comprehensive yearly overview with trends and breakdowns
- **Category Analysis**: Visual breakdown of income and expenses by category

### 🎨 User Interface
- Modern, responsive design using Bootstrap 5
- Interactive charts and graphs using Chart.js
- Clean dashboard with key financial metrics
- Easy-to-use forms with validation
- Mobile-friendly interface

### 🔐 Security Features
- User authentication and authorization
- Secure password handling
- Session management
- CSRF protection
- SQL injection protection
- Environment-based configuration

---

## 🛠 Technology Stack

- **Backend**: Django 4.2.9
- **Database**: PostgreSQL 15
- **Frontend**: Bootstrap 5, Chart.js
- **Forms**: Django Crispy Forms with Bootstrap 4
- **Server**: Gunicorn
- **Containerization**: Docker & Docker Compose
- **Orchestration**: Kubernetes with Helm charts
- **Static Files**: WhiteNoise

---

## 🚀 Quick Start

### Docker Deployment

**Prerequisites**: Docker and Docker Compose installed

1. **Clone and navigate to the project**
   ```bash
   git clone <repository-url>
   cd budget-app-final
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your values (or use defaults for development)
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - URL: http://localhost:8000
   - Default admin credentials:
     - Username: `admin`
     - Password: `admin`
   
   ⚠️ **Change the default password immediately!**

5. **Stop the application**
   ```bash
   docker-compose down
   ```

---

### Kubernetes/Helm Deployment

**Prerequisites**: Kubernetes cluster, kubectl, and Helm 3 installed

#### Quick Deployment

1. **Create custom values file**
   ```bash
   cp helm/budget-app/values.yaml helm/budget-app/values-production.yaml
   ```

2. **Edit with your actual secrets**
   ```bash
   nano helm/budget-app/values-production.yaml
   ```
   
   Update these critical values:
   - `app.env.djangoSecretKey`: Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
   - `postgres.env.password`: Strong database password
   - `app.env.djangoAllowedHosts`: Your domain (e.g., `budget.example.com,localhost`)
   - `app.env.csrfTrustedOrigins`: `https://your-domain.com`
   - `ingress.hosts[0].host`: Your domain
   - `ingress.tls[0].hosts[0]`: Your domain

3. **Deploy with Helm**
   ```bash
   helm install budget-app ./helm/budget-app \
     -f ./helm/budget-app/values-production.yaml \
     --namespace budget \
     --create-namespace
   ```

4. **Verify deployment**
   ```bash
   # Check pods
   kubectl get pods -n budget
   
   # Check services
   kubectl get svc -n budget
   
   # Check ingress
   kubectl get ingress -n budget
   
   # View logs
   kubectl logs -f deployment/budget-app -n budget
   ```

5. **Upgrade deployment**
   ```bash
   helm upgrade budget-app ./helm/budget-app \
     -f ./helm/budget-app/values-production.yaml \
     --namespace budget
   ```

6. **Uninstall**
   ```bash
   helm uninstall budget-app --namespace budget
   kubectl delete namespace budget
   ```

**📝 Note**: Your `values-production.yaml` is automatically ignored by Git (in `.gitignore`).

For detailed Helm deployment options, see `helm/budget-app/DEPLOYMENT.md`.

---

### Manual Installation

**Prerequisites**: Python 3.11+, PostgreSQL 15+

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd budget-app-final
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL**
   ```bash
   sudo -u postgres psql
   ```
   ```sql
   CREATE DATABASE budget_db;
   CREATE USER budget_user WITH PASSWORD 'your_secure_password';
   ALTER ROLE budget_user SET client_encoding TO 'utf8';
   ALTER ROLE budget_user SET default_transaction_isolation TO 'read committed';
   ALTER ROLE budget_user SET timezone TO 'UTC';
   GRANT ALL PRIVILEGES ON DATABASE budget_db TO budget_user;
   \q
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

6. **Run migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

9. **Run development server**
   ```bash
   python manage.py runserver
   ```

10. **Access application**
    - URL: http://localhost:8000

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file from `.env.example`:

```bash
# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here-minimum-50-characters
SECRET_KEY=your-secret-key-here-minimum-50-characters
DJANGO_DEBUG=False
DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com

# Database Configuration
DB_NAME=budget_db
DB_USER=budget_user
DB_PASSWORD=your-secure-database-password
DB_HOST=db
DB_PORT=5432
POSTGRES_DB=budget_db
POSTGRES_USER=budget_user
POSTGRES_PASSWORD=your-secure-database-password

# Superuser (Optional - for initial setup only)
# DJANGO_SUPERUSER_USERNAME=admin
# DJANGO_SUPERUSER_EMAIL=admin@example.com
# DJANGO_SUPERUSER_PASSWORD=your-secure-admin-password

# Production Domain
DOMAIN=your-domain.com
```

### Generating Secure Secrets

**Django Secret Key:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Database Password:**
```bash
openssl rand -base64 32
```

⚠️ **Security Note**: Never commit your `.env` file to version control!

---

## 📖 Usage Guide

### First-Time Setup

1. **Login or Register**
   - Access http://localhost:8000
   - Login with admin credentials or register a new account
   - Default categories are created automatically

2. **Add Bank Accounts**
   - Navigate to "Accounts" → "Add Account"
   - Add checking, savings, credit cards, cash, or investment accounts
   - Set opening balances and account setup dates

3. **Create Custom Categories** (Optional)
   - Go to "Categories"
   - Add custom income or expense categories
   - Organize transactions to match your needs

4. **Record Income**
   - Click "Income" → "Add Income"
   - Select category (e.g., Salary, Freelance)
   - Choose destination bank account
   - Enter amount and description
   - Account balance updates automatically

5. **Record Expenses**
   - Click "Expenses" → "Add Expense"
   - Select category (e.g., Food, Transportation, Utilities)
   - Choose source bank account
   - Enter amount and description
   - Account balance updates automatically

6. **Set Monthly Budgets**
   - Navigate to "Budgets" → "Create Budget"
   - Set spending limits for expense categories
   - Track progress with visual indicators (green/yellow/red)

7. **Transfer Between Accounts**
   - Go to "Transfers" → "Add Transfer"
   - Select source and destination accounts
   - Enter amount
   - Both account balances update automatically

### Key Features

#### Dashboard
- Monthly and annual financial overview
- Total income, expenses, and savings
- Recent transactions
- Budget progress indicators
- Account balance summaries
- Quick action buttons

#### Reports
- **Monthly Summary**
  - Income vs Expenses comparison
  - Category breakdowns with pie charts
  - Account balances
  - Savings calculations
  - Month-over-month trends

- **Annual Summary**
  - Yearly trends with line graphs
  - Month-by-month breakdown
  - Category analysis across the year
  - Net worth calculations
  - Downloadable reports

#### Budget Tracking
- Set monthly limits per category
- Visual progress bars
- Color-coded warnings:
  - 🟢 Green: Under 75% of budget
  - 🟡 Yellow: 75-100% of budget
  - 🔴 Red: Over budget
- Remaining budget calculations
- Historical budget performance

---

## 📁 Project Structure

```
budget-app-final/
├── budget/                      # Main Django app
│   ├── models.py               # Database models
│   ├── views.py                # View logic
│   ├── forms.py                # Form definitions
│   ├── urls.py                 # URL routing
│   ├── admin.py                # Admin configuration
│   └── management/
│       └── commands/           # Custom Django commands
├── budget_project/             # Project settings
│   ├── settings.py             # Django configuration
│   ├── urls.py                 # Root URL config
│   └── wsgi.py                 # WSGI config
├── templates/                  # HTML templates
│   ├── base.html               # Base template
│   └── budget/                 # App templates
├── static/                     # Static files (CSS, JS)
├── helm/                       # Kubernetes Helm charts
│   └── budget-app/
│       ├── values.yaml         # Helm configuration
│       ├── templates/          # K8s manifests
│       └── DEPLOYMENT.md       # Helm deployment guide
├── docker-compose.yml          # Docker Compose config
├── Dockerfile                  # Docker build config
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

---

## 🔐 Security

### Best Practices

1. **Environment Variables**
   - ✅ Use `.env` file for sensitive data
   - ✅ Never commit `.env` to Git
   - ✅ Use `.env.example` as template
   - ✅ Generate strong random secrets

2. **Production Settings**
   - ✅ Set `DEBUG=False`
   - ✅ Use strong `SECRET_KEY` (50+ characters)
   - ✅ Configure proper `ALLOWED_HOSTS`
   - ✅ Use HTTPS with valid SSL certificate
   - ✅ Set `CSRF_TRUSTED_ORIGINS`

3. **Database Security**
   - ✅ Use strong database passwords (16+ characters)
   - ✅ Restrict database access
   - ✅ Enable database backups
   - ✅ Use different credentials per environment

4. **User Management**
   - ✅ Change default admin password
   - ✅ Use strong passwords for all accounts
   - ✅ Disable superuser auto-creation in production
   - ✅ Implement password policies

5. **Kubernetes Security**
   - ✅ Use Kubernetes Secrets for sensitive data
   - ✅ Never commit `values-production.yaml`
   - ✅ Limit namespace access
   - ✅ Enable RBAC
   - ✅ Use network policies

### Security Checklist

Before deploying to production:

- [ ] Generated unique Django secret key
- [ ] Created strong database password
- [ ] Set `DEBUG=False`
- [ ] Configured `ALLOWED_HOSTS` with actual domain
- [ ] Set `CSRF_TRUSTED_ORIGINS` with actual domain
- [ ] Changed default admin credentials
- [ ] Configured SSL/TLS certificates
- [ ] Disabled superuser auto-creation
- [ ] Set up database backups
- [ ] Configured logging and monitoring
- [ ] Reviewed all environment variables
- [ ] Tested deployment in staging environment

### What to Never Commit

- ❌ `.env` files
- ❌ `values-production.yaml` or `values-*.yaml`
- ❌ Database dumps with real data
- ❌ Secret keys or passwords
- ❌ SSL certificates
- ❌ Access tokens or API keys

---

## 🐛 Troubleshooting

### Docker Issues

**Port already in use:**
```bash
# Stop all containers
docker-compose down

# Find and kill process using port
# macOS/Linux
lsof -ti:8000 | xargs kill
lsof -ti:5432 | xargs kill

# Windows
netstat -ano | findstr :8000
# Kill using Task Manager
```

**Database connection errors:**
```bash
# Restart services
docker-compose down
docker-compose up -d

# View logs
docker-compose logs -f db
```

**Reset everything (deletes all data):**
```bash
docker-compose down -v
docker-compose up --build
```

### Kubernetes Issues

**Pods not starting:**
```bash
# Check pod status
kubectl get pods -n budget

# Describe pod for details
kubectl describe pod <pod-name> -n budget

# View logs
kubectl logs <pod-name> -n budget

# Check events
kubectl get events -n budget --sort-by='.lastTimestamp'
```

**Database connection issues:**
```bash
# Check postgres pod
kubectl logs postgres-<pod-id> -n budget

# Check secret
kubectl get secret budget-app-secret -n budget -o yaml

# Restart pods
kubectl rollout restart deployment/budget-app -n budget
kubectl rollout restart deployment/postgres -n budget
```

**Ingress not working:**
```bash
# Check ingress
kubectl describe ingress -n budget

# Verify ingress controller is running
kubectl get pods -n kube-system | grep traefik

# Check certificate
kubectl get certificate -n budget
```

### Application Issues

**Static files not loading:**
```bash
# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Or in Kubernetes
kubectl exec -it deployment/budget-app -n budget -- python manage.py collectstatic --noinput
```

**Database migrations needed:**
```bash
# Docker
docker-compose exec web python manage.py migrate

# Kubernetes
kubectl exec -it deployment/budget-app -n budget -- python manage.py migrate
```

**Create superuser:**
```bash
# Docker
docker-compose exec web python manage.py createsuperuser

# Kubernetes
kubectl exec -it deployment/budget-app -n budget -- python manage.py createsuperuser
```

---

## 🔧 Development

### Running Tests
```bash
python manage.py test
```

### Django Shell
```bash
# Local
python manage.py shell

# Docker
docker-compose exec web python manage.py shell

# Kubernetes
kubectl exec -it deployment/budget-app -n budget -- python manage.py shell
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Useful Docker Commands
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Execute Django commands
docker-compose exec web python manage.py <command>

# Access database
docker-compose exec db psql -U budget_user -d budget_db
```

### Useful Kubernetes Commands
```bash
# Get all resources
kubectl get all -n budget

# Port forward to access locally
kubectl port-forward svc/budget-app 8000:8000 -n budget

# Execute command in pod
kubectl exec -it deployment/budget-app -n budget -- bash

# View all logs
kubectl logs -f deployment/budget-app -n budget --all-containers=true
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- Inspired by [budget_expense_management](https://github.com/minupjames/budget_expense_management/)
- Built with Django and Bootstrap
- Charts powered by Chart.js
- Container orchestration with Kubernetes and Helm

---

## 📞 Support

For issues, questions, or contributions:
- Open an issue on the repository
- Check existing documentation in `helm/budget-app/DEPLOYMENT.md`
- Review troubleshooting section above

---

**Built with ❤️ using Django**

