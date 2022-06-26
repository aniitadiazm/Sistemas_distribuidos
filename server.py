#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-

import random
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
    
    def getMainService(self):
        
        active = False
        while self.mainServices != {} and active == False:
            randomMain = random.choice(list(self.mainServices.values()))
            
            try:
                randomMain.ice_ping()
                active = True
                
            except:
                active = False
                del self.mainServices[randomMain]
                
        if self.mainServices == {}:
            raise IceFlix.TemporaryUnavailable
        
        main_service = IceFlix.MainPrx.checkedCast(randomMain)
        return main_service