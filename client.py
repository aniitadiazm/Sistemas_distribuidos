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

class Client(Ice.Application):

    def __init__(self):

        self.main_service = None
        self.admin_token = None

    
    def comprobar_argumentos(self):

        if len(sys.argv) != 3:
            print(f"\n Número de argumentos incorrectos: "
                "python3 client.py <main_proxy> <admin_token>.\n")

            sys.exit(1)
    
    def run(self, argv):

        self.comprobar_argumentos
        self.admin_token = argv[2]
        proxy = self.communicator().stringToProxy(argv[1])
        
        try:
            self.main_service = IceFlix.MainPrx.checkedCast(proxy)
            if not self.main_service.isAdmin(self.admin_token):
                sys.exit(1)


        except:
            print(f"\n Servicio no disponible ")

        
if __name__ == "__main__":
    sys.exit(Client().main(sys.argv))
