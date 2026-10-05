# Production Deployment Checklist

1. Set ENVIRONMENT=production.
2. Set a strong ADMIN_TOKEN.
3. Use managed PostgreSQL.
4. Configure AI and search secrets only when needed.
5. Keep EMAIL_PROVIDER disabled until outbound email is explicitly approved.
6. Verify /health and /ready.
7. Run pytest and compileall before deployment.
