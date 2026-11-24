# Migraciones de SQL Server

Ejecute la migración desde SQL Server Management Studio o `sqlcmd`:

```powershell
sqlcmd -S localhost,1433 -d Autopartes_Gallegos -U <usuario> -P <password> -C -i backend/migrations/001_scraping_schema.sql
```

La migración es idempotente y no elimina ni recrea registros.

Incluye:

- Secuencias para identificadores de `Producto_externo` e `Historial_precio`.
- Restricciones predeterminadas que permiten insertar sin asignar IDs manualmente.
- Índice único por proveedor, sucursal y código externo.
- Índices de consulta para historial y ejecuciones.
- Contadores de la ejecución general y manual.
- Relaciones adicionales entre historial y ejecución.