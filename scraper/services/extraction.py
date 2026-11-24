
from scraper.services.normalization import (
    normalizar_productos_sagaji
)

from scraper.exporters.csv_exporter import (
    exportar_productos
)


def ejecutar_extraccion_sagaji(
    client,
    termino,
    tipo_busqueda="Descripcion",
    cuantos=None,
    exportar_csv=True
):

    # 1. Recuperar todos los productos.
    resultado = client.buscar_todos_por_descripcion(
        termino=termino,
        cuantos=cuantos or 10,
        tipo_busqueda=tipo_busqueda
    )

    productos_originales = resultado["productos"]

    # 2. Normalizar los productos.
    productos_normalizados = normalizar_productos_sagaji(
        productos_originales
    )

    # 3. Exportar los resultados.
    ruta_archivo = None
    if exportar_csv:
        ruta_archivo = exportar_productos(
            productos_normalizados,
            proveedor="sagaji"
        )

    return {
        "resultado_original": resultado,
        "productos_normalizados": productos_normalizados,
        "archivo": ruta_archivo
    }
