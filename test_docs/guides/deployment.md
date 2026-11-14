# Deployment Guide

This guide covers deploying PulseAPI to a production Kubernetes cluster.

## Prerequisites
- Kubernetes `v1.29+`
- Helm `v3.14+`
- Managed Redis and PostgreSQL instances

## Deployment Steps
1. **Create Namespace & Secrets:**
   ```bash
   kubectl create namespace pulse-prod
   kubectl create secret generic pulse-secrets \
     --from-literal=DATABASE_URL="postgres://..." \
     --from-literal=REDIS_URL="redis://..." \
     -n pulse-prod
   ```
2. **Install via Helm:**
   ```bash
   helm upgrade --install pulse-api ./charts/pulse \
     --namespace pulse-prod \
     --values ./charts/pulse/values-prod.yaml
   ```
3. **Verify Health:**
   Run `kubectl get pods -n pulse-prod` and confirm all replicas show `1/1 Running`.