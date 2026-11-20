
from scraper.services.normalization import (
    normalizar_productos_sagaji
)

from scraper.exporters.csv_exporter import (
    exportar_productos
)


def ejecutar_extraccion_sagaji(client, termino):

    print("\nIniciando extracción de SAGAJI...")

    # 1. Recuperar todos los productos.
    resultado = client.buscar_todos_por_descripcion(
        termino=termino,
        cuantos=10
    )

    productos_originales = resultado["productos"]

    print(
        f"\nProductos recuperados: "
        f"{len(productos_originales)}"
    )

    # 2. Normalizar los productos.
    productos_normalizados = normalizar_productos_sagaji(
        productos_originales
    )

    print(
        f"Productos normalizados: "
        f"{len(productos_normalizados)}"
    )

    # 3. Exportar los resultados.
    ruta_archivo = exportar_productos(
        productos_normalizados,
        proveedor="sagaji"
    )

    print("\nRESUMEN DE EXTRACCIÓN")
    print("-" * 45)
    print("Término:", termino)
    print("Páginas consultadas:", resultado["total_paginas"])
    print("Productos recuperados:", len(productos_originales))
    print("Productos normalizados:", len(productos_normalizados))
    print("Productos únicos:", resultado["total_productos_unicos"])
    print("Archivo generado:", ruta_archivo)

    return {
        "resultado_original": resultado,
        "productos_normalizados": productos_normalizados,
        "archivo": ruta_archivo
    }
