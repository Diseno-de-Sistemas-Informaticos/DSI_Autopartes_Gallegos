
import os
import time
import requests

from dotenv import load_dotenv


load_dotenv()


class SagajiClient:

    BASE_URL = "https://ecommerce.sagaji.com.mx/ecommerce/MVC"
    HOME_URL = "https://ecommerce.sagaji.com.mx/ecommerce/"

    def __init__(
        self,
        max_retries=None,
        request_delay=None,
        timeout=30
    ):

        self.usuario = os.getenv("SAGAJI_USER")
        self.password = os.getenv("SAGAJI_PASSWORD")
        self.recordar = os.getenv("SAGAJI_REMEMBER", "0")

        if not self.usuario or not self.password:
            raise ValueError(
                "Configura SAGAJI_USER y SAGAJI_PASSWORD en .env"
            )

        self.max_retries = (
            int(max_retries)
            if max_retries is not None
            else int(os.getenv("SCRAPING_MAX_RETRIES", "3"))
        )
        self.request_delay = (
            float(request_delay)
            if request_delay is not None
            else float(os.getenv("SCRAPING_REQUEST_DELAY", "1"))
        )
        self.timeout = timeout
        self.session = requests.Session()

        self.session.headers.update({
            "Referer": self.HOME_URL,
            "Accept": "application/json, text/javascript, */*; q=0.01"
        })

        self.autenticado = False
        self.filial = None
        self.canal = None
        self.login = None

    def _get_with_retries(self, url, params=None, reauth=True):
        ultimo_error = None

        for intento in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )

                if response.status_code == 205 and reauth:
                    self.autenticado = False
                    self.iniciar_sesion()
                    continue

                if response.status_code in {429, 500, 502, 503, 504}:
                    ultimo_error = RuntimeError(
                        f"Error temporal HTTP {response.status_code}"
                    )
                else:
                    return response

            except requests.RequestException as error:
                ultimo_error = error

            if intento < self.max_retries:
                time.sleep(self.request_delay * intento)

        if ultimo_error:
            raise RuntimeError(
                "No fue posible completar la solicitud temporal de SAGAJI."
            ) from ultimo_error

        raise RuntimeError("No fue posible completar la solicitud a SAGAJI.")

    def iniciar_sesion(self):

        self._get_with_retries(
            self.HOME_URL,
            reauth=False
        )

        params = {
            "usuario": self.usuario,
            "password": self.password,
            "recordar": self.recordar,
            "id": "IniciaSesion"
        }

        response = self._get_with_retries(
            self.BASE_URL,
            params=params,
            reauth=False
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
        cuantos=10,
        tipo_busqueda="Descripcion"
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
            "noparte": termino if tipo_busqueda == "Codigo" else "",
            "valor": "" if tipo_busqueda == "Codigo" else termino,
            "categoria": "",
            "lineas": "",
            "familias": "",
            "id": "AutopartesDescripcion"
        }

        response = self._get_with_retries(
            self.BASE_URL,
            params=params,
            reauth=True
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
        max_paginas=None,
        tipo_busqueda="Descripcion"
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
            cuantos=cuantos,
            tipo_busqueda=tipo_busqueda
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

        if max_paginas is not None and total_paginas > max_paginas:
            raise RuntimeError(
                f"La consulta requiere {total_paginas} páginas. "
                f"Se superó el límite de seguridad de {max_paginas}."
            )

        todos_los_productos = list(productos)

        # Consultamos las páginas restantes.
        for numero_pagina in range(1, total_paginas):

            respuesta = self.buscar_por_descripcion(
                termino=termino,
                pagina=numero_pagina,
                cuantos=cuantos,
                tipo_busqueda=tipo_busqueda
            )

            productos_pagina = respuesta.get("productos", [])

            todos_los_productos.extend(productos_pagina)

            if self.request_delay > 0:
                time.sleep(self.request_delay)

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
