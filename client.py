#!/usr/bin/python3
# -*- coding: utf-8 -*-hashlib


# pylint: disable=C0103
# pylint: disable=C0301
# pylint: disable=C0113
# pylint: disable=E0401
# pylint: disable=C0103
# pylint: disable=C0411
# pylint: disable=C0413
# pylint: disable=W0613

import Ice
import IceStorm
Ice.loadSlice('IceFlix.ice')
import IceFlix
import sys
import hashlib
from getpass import getpass

class Client(Ice.Application):

    def __init__(self):

        self.main_service = None
        self.admin_token = None

    
    def comprobar_argumentos(self):

        if len(sys.argv) != 3:
            print(f"\n Número de argumentos incorrectos: "
                "python3 client.py <main_proxy> <admin_token>.\n")

            sys.exit(1)
    
    def select_option(self, choice):

        """Método que devulve un servicio en función de una opción."""

        try:
            if choice == 1:
                return self.main_service.getAuthenticator()

            elif choice == 2:
                return self.main_service.getCatalog()

            else:
                print(f"Saliendo...")

        except IceFlix.TemporaryUnavailable as ice_flix_error:
            print(f"{ice_flix_error}\nServicio no disponible.")
    
    def run(self, argv):

        intentos = 3
        self.comprobar_argumentos
        self.admin_token = argv[2]
        proxy = self.communicator().stringToProxy(argv[1])
        
        # try:
        #     self.main_service = IceFlix.MainPrx.checkedCast(proxy)
        #     if not self.main_service.isAdmin(self.admin_token):
        #         sys.exit(1)


        # except:
        #     print(f"\n Servicio no disponible ")

        while True:
            if intentos != 0:

                try:
                    self.main_service = IceFlix.MainPrx.checkedCast(proxy)
                    self.main_service.isAdmin(self.admin_token)
                    break

                except:
                    print("1")
                    print(f"\nServicio no disponible ")
                    print("2")
                    print(f"\nIntentos: {intentos} \n")
                    # time.sleep(5)

                    try:
                        proxy_intento = input("\nIntroduce el proxy nuevamente: ")
                        proxy = self.communicator().stringToProxy(proxy_intento)
                        intentos = intentos - 1

                    except:
                        print(f"\nProxy no detectado ")

            else:
                print(f"\nConexión NO establecida.\n")
                sys.exit(1)

        while True:
            if self.main_service.isAdmin(self.admin_token):
                print(f"\n TOKEN introducido CORRECTO")

                choice = int(self.show_menu())
                service = self.select_option(choice)

                if (choice == 1) and (service is not None):
                    self.menu_authentication(service)


                elif (choice == 2) and (service is not None):
                    self.menu_catalog(service)

                elif choice == 3:
                    sys.exit(0)

                else:
                    print("Introduzca una opción válida.")
                    
            else:
                print(f"\n TOKEN introducido NO CORRECTO")
                self.admin_token = input("Introduce un TOKEN válido: ")
    
    def establecer_rango_opciones(self, mn, mx) -> int:

        """Método que comprueba que la opción del menú es un entero válido."""

        while True:
            option = input()

            if not int(option.isdigit()) or (int(option) < mn or int(option) > mx):
                print(f"Rango de opciones [{str(mn)}-{str(mx)}]")

            else:
                break

        return int(option)

    def show_menu(self) -> int:

        """Método que muestra el menú principal."""

        print(
            f"""\n-- MENÚ PRINCIPAL --\n Selecciona que desea hacer: \n1.- Autenticarse en el sistema. \n2.- Catalogo del sistema. \n3.- Salir del sistema.\n"""
        )

        return int(self.establecer_rango_opciones(1, 3))
    
    def menu_authentication(self, service):

         while True:
            print(f"""\n-- MENÚ AUTHENTICATOR --\nSelecciona que desea hacer:\n1.- Crear nuevo token de autorizacion\n2.- Comprobar token
        3.- Buscar usuario por TOKEN.\n4.- Añadir usuario\n5.- Eliminar usuario\n6.- Salir del menú autenticación\n""")

            choice = int(self.establecer_rango_opciones(1, 6))
    
            if choice == 1:
                try:
                    user = input("\nIntroduce el usuario: ")
                    password = getpass("\nIntroduce la contraseña: ")
                    password_hash = hashlib.sha256(password.encode()).hexdigest()

                #     self.user_token = service.refreshAuthorization(self.user, self.password_hash)
                #     self.publicador_revocation = self.suscripcion_user_revocations(self.user, self.password_hash)
                #     print(f"\nTOKEN generado correctamente")
                    print(service.refreshAuthorization(user, password_hash))

                except IceFlix.Unauthorized as ice_flix_error:
                    print(f"{ice_flix_error}\nUSUARIO no registrado")


        
if __name__ == "__main__":
    sys.exit(Client().main(sys.argv))
