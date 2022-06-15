#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-

import Ice
import IceStorm
Ice.loadSlice('IceFlix.ice')
import IceFlix

class Services(Ice.Application):
    
    """ Contiene todos los servicios necesarios para ejecutar la aplicación """
    
    def __init__(self):
        
        """ Inicializar todos los microservicios """
                
        super().__init__()
        self.mainServices = {}
        self.authServices = {}
        self.catalogServices = {}
        self.streamServices = {}