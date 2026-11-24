USE Autopartes_Gallegos;
GO

SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

/*
Migración de endurecimiento del módulo de scraping.
Es idempotente y no elimina ni modifica datos históricos existentes.
*/

IF OBJECT_ID('dbo.seq_producto_externo', 'SO') IS NULL
BEGIN
    CREATE SEQUENCE dbo.seq_producto_externo
        AS INT
        START WITH 1
        INCREMENT BY 1;
END;
GO

DECLARE @next_producto_externo INT =
    COALESCE((SELECT MAX(id_producto_externo) + 1 FROM Producto_externo), 1);
DECLARE @sql_producto_externo NVARCHAR(200);
SET @sql_producto_externo =
    N'ALTER SEQUENCE dbo.seq_producto_externo RESTART WITH ' +
    CONVERT(NVARCHAR(20), @next_producto_externo);
EXEC sp_executesql @sql_producto_externo;
GO

IF OBJECT_ID('dbo.seq_historial_precio', 'SO') IS NULL
BEGIN
    CREATE SEQUENCE dbo.seq_historial_precio
        AS INT
        START WITH 1
        INCREMENT BY 1;
END;
GO

DECLARE @next_historial_precio INT =
    COALESCE((SELECT MAX(id_historial) + 1 FROM Historial_precio), 1);
DECLARE @sql_historial_precio NVARCHAR(200);
SET @sql_historial_precio =
    N'ALTER SEQUENCE dbo.seq_historial_precio RESTART WITH ' +
    CONVERT(NVARCHAR(20), @next_historial_precio);
EXEC sp_executesql @sql_historial_precio;
GO

IF COL_LENGTH('Producto_externo', 'id_proveedor') IS NULL
    ALTER TABLE Producto_externo ADD id_proveedor INT NULL;
GO

IF COL_LENGTH('Producto_externo', 'sucursal_externa') IS NULL
    ALTER TABLE Producto_externo ADD sucursal_externa VARCHAR(150) NULL;
GO

IF COL_LENGTH('Producto_externo', 'descripcion_externa') IS NULL
    ALTER TABLE Producto_externo ADD descripcion_externa VARCHAR(500) NULL;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.foreign_keys
    WHERE name = 'FK_ProductoExterno_Proveedor'
)
BEGIN
    ALTER TABLE Producto_externo
    ADD CONSTRAINT FK_ProductoExterno_Proveedor
    FOREIGN KEY (id_proveedor) REFERENCES Proveedor(id_proveedor);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.default_constraints
    WHERE name = 'DF_ProductoExterno_Id'
      AND parent_object_id = OBJECT_ID('Producto_externo')
)
BEGIN
    ALTER TABLE Producto_externo
    ADD CONSTRAINT DF_ProductoExterno_Id
    DEFAULT (NEXT VALUE FOR dbo.seq_producto_externo)
    FOR id_producto_externo;
END;
GO

IF COL_LENGTH('Historial_precio', 'id_ejecucion') IS NULL
    ALTER TABLE Historial_precio ADD id_ejecucion INT NULL;
GO

IF COL_LENGTH('Historial_precio', 'moneda') IS NULL
    ALTER TABLE Historial_precio
    ADD moneda CHAR(3) NOT NULL
    CONSTRAINT DF_HistorialPrecio_Moneda DEFAULT 'MXN';
GO

IF COL_LENGTH('Historial_precio', 'disponible') IS NULL
    ALTER TABLE Historial_precio ADD disponible BIT NULL;
GO

IF COL_LENGTH('Historial_precio', 'existencia_reportada') IS NULL
    ALTER TABLE Historial_precio ADD existencia_reportada INT NULL;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.foreign_keys
    WHERE name = 'FK_HistorialPrecio_Ejecucion'
)
BEGIN
    ALTER TABLE Historial_precio
    ADD CONSTRAINT FK_HistorialPrecio_Ejecucion
    FOREIGN KEY (id_ejecucion) REFERENCES Ejecucion_scraping(id_ejecucion);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.default_constraints
    WHERE name = 'DF_HistorialPrecio_Id'
      AND parent_object_id = OBJECT_ID('Historial_precio')
)
BEGIN
    ALTER TABLE Historial_precio
    ADD CONSTRAINT DF_HistorialPrecio_Id
    DEFAULT (NEXT VALUE FOR dbo.seq_historial_precio)
    FOR id_historial;
END;
GO

IF COL_LENGTH('Ejecucion_scraping', 'productos_nuevos') IS NULL
    ALTER TABLE Ejecucion_scraping
    ADD productos_nuevos INT NOT NULL
    CONSTRAINT DF_EjecucionProductosNuevos DEFAULT 0;
GO

IF COL_LENGTH('Ejecucion_scraping', 'precios_modificados') IS NULL
    ALTER TABLE Ejecucion_scraping
    ADD precios_modificados INT NOT NULL
    CONSTRAINT DF_EjecucionPreciosModificados DEFAULT 0;
GO

IF COL_LENGTH('Ejecucion_scraping', 'articulos_consultados') IS NULL
    ALTER TABLE Ejecucion_scraping
    ADD articulos_consultados INT NOT NULL
    CONSTRAINT DF_EjecucionArticulosConsultados DEFAULT 0;
GO

IF COL_LENGTH('Ejecucion_scraping', 'errores_encontrados') IS NULL
    ALTER TABLE Ejecucion_scraping
    ADD errores_encontrados INT NOT NULL
    CONSTRAINT DF_EjecucionErroresEncontrados DEFAULT 0;
GO

IF EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_EjecucionScraping_Tipo'
)
BEGIN
    ALTER TABLE Ejecucion_scraping
    DROP CONSTRAINT CK_EjecucionScraping_Tipo;
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_EjecucionScraping_Tipo'
)
BEGIN
    ALTER TABLE Ejecucion_scraping
    ADD CONSTRAINT CK_EjecucionScraping_Tipo
    CHECK (tipo_busqueda IN ('Codigo', 'Descripcion', 'General'));
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'UX_ProductoExterno_Proveedor_Sucursal_Codigo'
      AND object_id = OBJECT_ID('Producto_externo')
)
BEGIN
    CREATE UNIQUE INDEX UX_ProductoExterno_Proveedor_Sucursal_Codigo
    ON Producto_externo (id_proveedor, sucursal_externa, codigo_externo)
    WHERE id_proveedor IS NOT NULL AND codigo_externo IS NOT NULL;
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_HistorialPrecio_Producto_Fecha'
      AND object_id = OBJECT_ID('Historial_precio')
)
BEGIN
    CREATE INDEX IX_HistorialPrecio_Producto_Fecha
    ON Historial_precio (id_producto_externo, fecha_captura DESC);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_EjecucionScraping_Fecha'
      AND object_id = OBJECT_ID('Ejecucion_scraping')
)
BEGIN
    CREATE INDEX IX_EjecucionScraping_Fecha
    ON Ejecucion_scraping (fecha_inicio DESC);
END;
GO