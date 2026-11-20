
import os
import requests

from dotenv import load_dotenv


load_dotenv()


class SagajiClient:

    BASE_URL = "https://ecommerce.sagaji.com.mx/ecommerce/MVC"
    HOME_URL = "https://ecommerce.sagaji.com.mx/ecommerce/"

    def __init__(self):

        self.usuario = os.getenv("SAGAJI_USER")
        self.password = os.getenv("SAGAJI_PASSWORD")
        self.recordar = os.getenv("SAGAJI_REMEMBER", "0")

        if not self.usuario or not self.password:
            raise ValueError(
                "Configura SAGAJI_USER y SAGAJI_PASSWORD en .env"
            )

        self.session = requests.Session()

        self.session.headers.update({
            "Referer": self.HOME_URL,
            "Accept": "application/json, text/javascript, */*; q=0.01"
        })

        self.autenticado = False
        self.filial = None
        self.canal = None
        self.login = None

    def iniciar_sesion(self):

        self.session.get(
            self.HOME_URL,
            timeout=30
        )

        params = {
            "usuario": self.usuario,
            "password": self.password,
            "recordar": self.recordar,
            "id": "IniciaSesion"
        }

        response = self.session.get(
            self.BASE_URL,
            params=params,
            timeout=30
        )

        if response.status_code == 205:
            raise RuntimeError("La sesión no pudo establecerse.")

        if response.status_code != 200:
            raise RuntimeError(
                f"Error HTTP durante el inicio de sesión: "
                f"{response.status_code}"
            )

        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(
                "El servidor no devolvió una respuesta JSON válida."
            )

        if not isinstance(data, dict):
            raise RuntimeError("Respuesta de autenticación inesperada.")

        if data.get("error") or data.get("exception"):
            raise RuntimeError(
                "SAGAJI rechazó la autenticación. "
                "Revisa las credenciales y el mensaje del portal."
            )

        campos = ["clfilial", "clcanal", "cllogin"]

        if not all(data.get(campo) for campo in campos):
            raise RuntimeError(
                "No se recibieron los datos de usuario esperados."
            )

        self.filial = data["clfilial"]
        self.canal = data["clcanal"]
        self.login = data["cllogin"]

        self.autenticado = True

        return True

    def buscar_por_descripcion(
        self,
        termino,
        pagina=0,
        cuantos=10
    ):

        if not self.autenticado:
            raise RuntimeError(
                "Primero debes iniciar sesión."
            )

        params = {
            "filial": self.filial,
            "canal": self.canal,
            "usuario": self.login,
            "pagina": pagina,
            "cuantos": cuantos,
            "armadora": "",
            "modelo": "",
            "periodo": "",
            "motor": "",
            "cilindro": "",
            "familia": "",
            "noparte": "",
            "valor": termino,
            "categoria": "",
            "lineas": "",
            "familias": "",
            "id": "AutopartesDescripcion"
        }

        response = self.session.get(
            self.BASE_URL,
            params=params,
            timeout=30
        )

        if response.status_code == 205:
            self.autenticado = False
            raise RuntimeError("La sesión de SAGAJI ha expirado.")

        if response.status_code != 200:
            raise RuntimeError(
                f"Error HTTP al consultar productos: "
                f"{response.status_code}"
            )

        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(
                "La consulta no devolvió JSON válido."
            )

        if not isinstance(data, dict) or data.get("error"):
            raise RuntimeError(
                "SAGAJI devolvió un error al consultar productos."
            )

        return data

    def buscar_todos_por_descripcion(
        self,
        termino,
        cuantos=10,
        max_paginas=100
    ):
        """
        Recupera todas las páginas disponibles para una búsqueda.

        Devuelve un diccionario con los productos encontrados
        y datos generales de la consulta.
        """

        # Primera consulta para conocer cuántas páginas existen.
        primera_respuesta = self.buscar_por_descripcion(
            termino=termino,
            pagina=0,
            cuantos=cuantos
        )

        informacion_paginas = primera_respuesta.get("paginas", {})
        productos = primera_respuesta.get("productos", [])

        if not isinstance(informacion_paginas, dict):
            raise RuntimeError(
                "La información de paginación tiene un formato inesperado."
            )

        total_paginas = int(
            informacion_paginas.get("totalPaginas", 1) or 1
        )

        total_elementos = int(
            informacion_paginas.get("totalElementos", len(productos)) or 0
        )

        if total_paginas < 1:
            total_paginas = 1

        if total_paginas > max_paginas:
            raise RuntimeError(
                f"La consulta requiere {total_paginas} páginas. "
                f"Se superó el límite de seguridad de {max_paginas}."
            )

        todos_los_productos = list(productos)

        # Consultamos las páginas restantes.
        for numero_pagina in range(1, total_paginas):

            print(
                f"Consultando página {numero_pagina + 1} "
                f"de {total_paginas}..."
            )

            respuesta = self.buscar_por_descripcion(
                termino=termino,
                pagina=numero_pagina,
                cuantos=cuantos
            )

            productos_pagina = respuesta.get("productos", [])

            todos_los_productos.extend(productos_pagina)

        # Eliminamos duplicados usando filial y número de parte.
        productos_unicos = []
        identificadores = set()

        for producto in todos_los_productos:

            identificador = (
                producto.get("filial"),
                producto.get("noparte")
            )

            if identificador not in identificadores:
                identificadores.add(identificador)
                productos_unicos.append(producto)

        return {
            "termino": termino,
            "total_paginas": total_paginas,
            "total_elementos_reportados": total_elementos,
            "total_productos_recuperados": len(todos_los_productos),
            "total_productos_unicos": len(productos_unicos),
            "productos": productos_unicos
        }
