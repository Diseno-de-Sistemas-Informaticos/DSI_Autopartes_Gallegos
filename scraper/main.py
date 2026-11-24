
from scraper.providers.sagaji_client import SagajiClient

from scraper.services.extraction import (
    ejecutar_extraccion_sagaji
)


def main():

    print("=" * 50)
    print("AUTOPARTES GALLEGOS")
    print("SISTEMA DE EXTRACCIÓN DE PRECIOS")
    print("=" * 50)

    client = SagajiClient()

    try:

        print("\nConectando con SAGAJI...")

        client.iniciar_sesion()

        print("Autenticación exitosa.")

        termino = input(
            "\nIntroduce un número de parte o descripción: "
        ).strip()

        if not termino:
            print("Debes introducir un término de búsqueda.")
            return

        ejecutar_extraccion_sagaji(
            client=client,
            termino=termino
        )

        print("\nProceso finalizado correctamente.")

    except Exception as error:

        print("\nOcurrió un error durante la extracción.")
        print("Detalle:", error)

    finally:
        client.session.close()


if __name__ == "__main__":
    main()
