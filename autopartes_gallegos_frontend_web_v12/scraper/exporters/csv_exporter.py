
import csv
import os
from datetime import datetime
from decimal import Decimal


def exportar_productos(productos, proveedor="sagaji"):

    os.makedirs("data/processed", exist_ok=True)

    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")

    ruta = os.path.join(
        "data",
        "processed",
        f"productos_{proveedor}_{fecha}.csv"
    )

    if not productos:
        print("No hay productos para exportar.")
        return None

    columnas = list(productos[0].keys())

    with open(
        ruta,
        mode="w",
        newline="",
        encoding="utf-8-sig"
    ) as archivo:

        escritor = csv.DictWriter(
            archivo,
            fieldnames=columnas
        )

        escritor.writeheader()

        for producto in productos:

            fila = producto.copy()

            # Convertimos Decimal a texto para conservar
            # su representación decimal en el CSV.
            for campo, valor in fila.items():
                if isinstance(valor, Decimal):
                    fila[campo] = str(valor)

            escritor.writerow(fila)

    return ruta
