# Deploy en Railway — gradeai-backend

## Servicios necesarios en Railway

1. **Service (este repo)** — conectar a GitHub con auto-deploy en `main`
2. **PostgreSQL Plugin** — agregar desde Railway dashboard → "Add Plugin" → PostgreSQL
3. **Volume** — crear en Railway dashboard → "Add Volume" → mount en `/app/uploads`

## Variables de entorno a configurar en Railway

| Variable            | Valor                                                              |
|---------------------|--------------------------------------------------------------------|
| `DATABASE_URL`      | Auto-inyectada por el plugin de PostgreSQL (no configurar a mano) |
| `ANTHROPIC_API_KEY` | Tu API key de Anthropic (`sk-ant-...`)                            |
| `JWT_SECRET`        | String aleatorio seguro — ver instrucciones abajo                 |
| `JWT_EXPIRE_MINUTES`| `1440`                                                             |
| `UPLOAD_DIR`        | `/app/uploads`                                                    |
| `FRONTEND_URL`      | URL del frontend en Railway (configurar después de desplegar FE)  |

## Cómo generar JWT_SECRET seguro

```bash
openssl rand -hex 32
```

## Orden de pasos

1. Crear proyecto en Railway
2. Agregar servicio → conectar este repo → rama `main`
3. Agregar plugin PostgreSQL → Railway inyecta `DATABASE_URL` automáticamente
4. Agregar Volume → configurar mount path `/app/uploads`
5. Configurar variables de entorno (todas excepto `DATABASE_URL`)
6. Hacer deploy → Railway ejecuta `alembic upgrade head` + `uvicorn` en cada deploy
7. Verificar health: `GET https://<tu-dominio>.up.railway.app/health`
8. Actualizar `FRONTEND_URL` con la URL del frontend una vez desplegado

## Notas importantes

- El `startCommand` en `railway.json` corre migraciones **antes** de levantar el servidor
- Los archivos subidos se persisten en el Volume; sin Volume, se pierden en cada redeploy
- El plugin PostgreSQL provee `DATABASE_URL` con SSL incluido — no requiere configuración extra
