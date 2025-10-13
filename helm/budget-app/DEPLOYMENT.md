# Helm Deployment Instructions

## 🚀 Quick Deployment

### Option 1: Edit values.yaml Directly (Simple)

1. **Edit the values file with your actual secrets:**
   ```bash
   nano helm/budget-app/values.yaml
   ```

2. **Update these values:**
   ```yaml
   app:
     env:
       djangoSecretKey: "your-actual-secret-key"
       djangoAllowedHosts: "your-domain.com,localhost"
       csrfTrustedOrigins: "https://your-domain.com"
   
   postgres:
     env:
       password: "your-actual-db-password"
   
   ingress:
     hosts:
       - host: your-domain.com
     tls:
       - hosts:
           - your-domain.com
   ```

3. **Deploy:**
   ```bash
   helm install budget-app ./helm/budget-app --namespace budget --create-namespace
   ```

4. **⚠️ IMPORTANT: Don't commit your changes to values.yaml!**
   - Keep your local changes uncommitted
   - Or revert them after deployment

---

### Option 2: Use Custom Values File (Recommended)

1. **Create a custom values file:**
   ```bash
   cp helm/budget-app/values.yaml helm/budget-app/values-production.yaml
   ```

2. **Edit with your actual secrets:**
   ```bash
   nano helm/budget-app/values-production.yaml
   ```

3. **Deploy with your custom file:**
   ```bash
   helm install budget-app ./helm/budget-app \
     -f ./helm/budget-app/values-production.yaml \
     --namespace budget \
     --create-namespace
   ```

4. **Add to .gitignore:**
   ```bash
   echo "helm/**/values-production.yaml" >> .gitignore
   echo "helm/**/values-*.yaml" >> .gitignore
   ```

---

### Option 3: Use --set Flags (For Small Changes)

```bash
helm install budget-app ./helm/budget-app \
  --set app.env.djangoSecretKey="your-secret-key" \
  --set postgres.env.password="your-db-password" \
  --set app.env.djangoAllowedHosts="your-domain.com,localhost" \
  --set ingress.hosts[0].host="your-domain.com" \
  --set ingress.tls[0].hosts[0]="your-domain.com" \
  --namespace budget \
  --create-namespace
```

---

## 🔄 Upgrading an Existing Deployment

```bash
# Option 1: With custom values file
helm upgrade budget-app ./helm/budget-app \
  -f ./helm/budget-app/values-production.yaml \
  --namespace budget

# Option 2: With direct edits to values.yaml
helm upgrade budget-app ./helm/budget-app \
  --namespace budget

# Option 3: With --set flags
helm upgrade budget-app ./helm/budget-app \
  --set app.env.djangoSecretKey="new-secret" \
  --namespace budget
```

---

## 🔍 Verifying Deployment

### Check Release Status
```bash
helm status budget-app --namespace budget
```

### List All Releases
```bash
helm list --namespace budget
```

### Check Pods
```bash
kubectl get pods -n budget
```

### View Logs
```bash
# Application logs
kubectl logs -f deployment/budget-app -n budget

# Database logs
kubectl logs -f deployment/postgres -n budget
```

### Check Ingress
```bash
kubectl get ingress -n budget
```

---

## 🧪 Testing Before Deployment

### Render templates without installing (dry-run):
```bash
helm template budget-app ./helm/budget-app \
  -f ./helm/budget-app/values-production.yaml \
  --namespace budget
```

### Validate templates:
```bash
helm lint ./helm/budget-app
```

---

## 🗑️ Uninstalling

```bash
# Uninstall the release
helm uninstall budget-app --namespace budget

# Delete the namespace (optional)
kubectl delete namespace budget
```

---

## 📋 Required Configuration Changes

Before deploying, you **must** change these values:

| Field | Current Placeholder | What to Set |
|-------|-------------------|-------------|
| `app.env.djangoSecretKey` | `REPLACE_WITH_YOUR_DJANGO_SECRET_KEY` | Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `postgres.env.password` | `REPLACE_WITH_YOUR_DB_PASSWORD` | Strong password (16+ chars) |
| `app.env.djangoAllowedHosts` | `your-domain.com,localhost` | Your actual domain |
| `app.env.csrfTrustedOrigins` | `https://your-domain.com` | Your actual domain with https:// |
| `ingress.hosts[0].host` | `your-domain.com` | Your actual domain |
| `ingress.tls[0].hosts[0]` | `your-domain.com` | Your actual domain |

---

## 🔑 Generating Secure Secrets

### Django Secret Key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Or online: https://djecrety.ir/

### Database Password:
Use a password manager or generate a strong password:
```bash
# Example: Generate 32 character password
openssl rand -base64 32
```

---

## 📚 Helm Commands Cheat Sheet

```bash
# Install
helm install <release-name> <chart-path> [flags]

# Upgrade
helm upgrade <release-name> <chart-path> [flags]

# Upgrade or install if doesn't exist
helm upgrade --install <release-name> <chart-path> [flags]

# Rollback to previous version
helm rollback <release-name> [revision]

# Get values of installed release
helm get values <release-name> -n <namespace>

# View history
helm history <release-name> -n <namespace>

# Uninstall
helm uninstall <release-name> -n <namespace>
```

---

## 🛡️ Security Best Practices

1. ✅ **Never commit** actual secrets to Git
2. ✅ Use **custom values files** (values-*.yaml) and add them to `.gitignore`
3. ✅ Generate **strong random secrets** for production
4. ✅ Use **different secrets** for each environment (dev/staging/prod)
5. ✅ Consider using **Kubernetes Secrets** or **sealed-secrets** for production
6. ✅ Set `djangoDebug: "False"` in production
7. ✅ Regularly **rotate secrets**

---

## 📞 Getting Help

```bash
# Get help on helm install
helm install --help

# Get notes about the chart
helm get notes budget-app -n budget

# Show all values that can be configured
helm show values ./helm/budget-app
```

