
from decimal import Decimal, InvalidOperation


def convertir_decimal(valor):
    """
    Convierte un valor numérico a Decimal.
    Evita problemas de precisión propios de float.
    """

    if valor is None or valor == "":
        return None

    try:
        return Decimal(str(valor).strip())
    except (InvalidOperation, ValueError):
        return None


def convertir_entero(valor):
    """
    Convierte un valor a entero.
    """

    if valor is None or valor == "":
        return None

    try:
        return int(Decimal(str(valor).strip()))
    except (InvalidOperation, ValueError):
        return None


def normalizar_producto_sagaji(producto):
    """
    Transforma un producto de SAGAJI
    a la estructura común del proyecto.
    """

    return {
        "proveedor": "SAGAJI",
        "filial": str(producto.get("filial") or "").strip(),
        "numero_parte": str(producto.get("noparte") or "").strip(),
        "descripcion": str(producto.get("descripcion") or "").strip(),
        "descripcion_larga": str(
            producto.get("descripcionlarga") or ""
        ).strip(),
        "marca": str(
            producto.get("descripcionlinea") or ""
        ).strip(),
        "familia": str(
            producto.get("descripcionfamilia") or ""
        ).strip(),
        "categoria": str(
            producto.get("descripcioncategoria") or ""
        ).strip(),
        "unidad_medida": str(
            producto.get("unidadmedida") or ""
        ).strip(),
        "especificacion": str(
            producto.get("especificacion") or ""
        ).strip(),
        "precio": convertir_decimal(producto.get("precio")),
        "existencia": convertir_entero(producto.get("existencia")),
        "multiplo_venta": convertir_decimal(
            producto.get("multiploventa")
        )
    }


def normalizar_productos_sagaji(productos):
    """
    Normaliza una lista completa de productos.
    """

    productos_normalizados = []

    for producto in productos:

        normalizado = normalizar_producto_sagaji(producto)

        # No almacenamos productos sin número de parte.
        if not normalizado["numero_parte"]:
            continue

        productos_normalizados.append(normalizado)

    return productos_normalizados
