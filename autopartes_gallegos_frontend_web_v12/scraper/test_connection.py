
import csv
import os
import requests

from scraper.providers.sagaji_client import SagajiClient


def exportar_csv(productos, termino):

    os.makedirs("data", exist_ok=True)

    ruta_archivo = os.path.join(
        "data",
        "productos_sagaji.csv"
    )

    if not productos:
        print("No hay productos para exportar.")
        return

    # Obtenemos todos los campos que aparezcan en los productos.
    columnas = list(dict.fromkeys(
        campo
        for producto in productos
        for campo in producto.keys()
    ))

    with open(
        ruta_archivo,
        mode="w",
        newline="",
        encoding="utf-8-sig"
    ) as archivo:

        escritor = csv.DictWriter(
            archivo,
            fieldnames=columnas,
            extrasaction="ignore"
        )

        escritor.writeheader()
        escritor.writerows(productos)

    print(f"\nArchivo CSV generado: {ruta_archivo}")


def main():

    print("Conectando con SAGAJI...")

    client = SagajiClient()

    try:

        client.iniciar_sesion()

        print("Autenticación exitosa.")
        print("Sesión HTTP establecida.")

        termino = input(
            "\nIntroduce un número de parte o descripción: "
        ).strip()

        if not termino:
            print("Debes introducir un término de búsqueda.")
            return

        print("\nIniciando extracción de productos...")

        resultado = client.buscar_todos_por_descripcion(
            termino=termino,
            cuantos=10
        )

        productos = resultado["productos"]

        print("\nRESUMEN DE EXTRACCIÓN")
        print("-" * 50)

        print("Término consultado:", resultado["termino"])
        print("Páginas consultadas:", resultado["total_paginas"])
        print(
            "Productos reportados por SAGAJI:",
            resultado["total_elementos_reportados"]
        )
        print(
            "Productos recuperados:",
            resultado["total_productos_recuperados"]
        )
        print(
            "Productos únicos:",
            resultado["total_productos_unicos"]
        )

        print("\nPRODUCTOS")
        print("-" * 50)

        for producto in productos:

            print("\nNúmero de parte:", producto.get("noparte"))
            print("Descripción:", producto.get("descripcion"))
            print("Marca:", producto.get("descripcionlinea"))
            print("Precio:", producto.get("precio"))
            print("Existencia:", producto.get("existencia"))

        exportar_csv(productos, termino)

        print("\nExtracción finalizada.")

    except requests.RequestException:
        print(
            "No fue posible establecer comunicación "
            "con SAGAJI."
        )

    except Exception as error:
        print("No se pudo completar la operación:", error)


if __name__ == "__main__":
    main()
