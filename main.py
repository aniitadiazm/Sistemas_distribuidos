"""Module containing a template for a main service."""

import logging
import uuid

import Ice
import IceStorm
import random

import IceFlix
from iceflix.service_announcement import (
    ServiceAnnouncementsListener,
    ServiceAnnouncementsSender,
)

TOKEN_ADMIN="admin"


class Main(IceFlix.Main):
    
    """ Servant for the IceFlix.Main interface.
    Disclaimer: this is demo code, it lacks of most of the needed methods
    for this interface. Use it with caution """

    def __init__(self):
        
        """ Create the Main servant instance """
        
        self.service_id = str(uuid.uuid4())

    def share_data_with(self, service):
        
        """ Share the current database with an incoming service """
        
        service.updateDB(None, self.service_id)

    def updateDB(self, values, service_id, current):  # pylint: disable=invalid-name,unused-argument
        
        """ Receives the current main service database from a peer """
        
        logging.info(
            "Receiving remote data base from %s to %s", service_id, self.service_id
        )


class MainApp(Ice.Application):
    
    """ Example Ice.Application for a Main service """

    def __init__(self):
        super().__init__()
        self.servant = Main()
        self.proxy = None
        self.adapter = None
        self.announcer = None
        self.subscriber = None

    def setup_announcements(self):
        
        """ Configure the announcements sender and listener """

        communicator = self.communicator()
        topic_manager = IceStorm.TopicManagerPrx.checkedCast(
            communicator.propertyToProxy("IceStorm.TopicManager"),
        )

        try:
            topic = topic_manager.create("ServiceAnnouncements")
        except IceStorm.TopicExists:
            topic = topic_manager.retrieve("ServiceAnnouncements")

        self.announcer = ServiceAnnouncementsSender(
            topic,
            self.servant.service_id,
            self.proxy,
        )

        self.subscriber = ServiceAnnouncementsListener(
            self.servant, self.servant.service_id, IceFlix.MainPrx
        )

        subscriber_prx = self.adapter.addWithUUID(self.subscriber)
        topic.subscribeAndGetPublisher({}, subscriber_prx)

    def run(self, args):
        
        """ Run the application, adding the needed objects to the adapter """
        
        logging.info("Running Main application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("Main")
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)

        self.setup_announcements()
        self.announcer.start_service()

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        self.announcer.stop()
        return 0
    
    def isAdmin(self, adminToken, current=None):
        
        """ Devuelve un valor booleano para comprobar si el token proporcionado
        corresponde o no con el administrativo """
        
        print(adminToken)
        if adminToken == TOKEN_ADMIN:
            return True
        return False
    
    def getAuthenticator(self, current=None):
        
        """ Devuelve un proxy a un servicio de autenticación """
        
        active = False
        while self.volatileServices.authenticators != [] and active is False:
            randomAuth = random.choice(self.volatileServices.authenticators)
            
            try:
                randomAuth.ice_ping()
                active = True
            except:
                active = False
                self.volatileServices.authenticators.remove(randomAuth)
        
        if self.volatileServices.authenticators == []:
            raise IceFlix.TemporaryUnavailable
        
        checked = IceFlix.AuthenticatorPrx.checkedCast(randomAuth)
        return checked
    
    def getCatalog(self, current=None):
        
        """ Devuelve un proxy a un servicio de catálogo """
        
        active = False
        while self.volatileServices.mediaCatalogs != [] and active is False:
            randomCatalog = random.choice(self.volatileServices.mediaCatalogs)
           
            try:
                randomCatalog.ice_ping()
                active = True
            except:
                active = False
                self.volatileServices.mediaCatalogs.remove(randomCatalog)
       
        if self.volatileServices.mediaCatalogs == []:
            raise IceFlix.TemporaryUnavailable
        
        checked = IceFlix.MediaCatalogPrx.checkedCast(randomCatalog)
        return checked

    def updateDB(self, currentDataBase, srvId, current=None):

        """ Actualiza la base de datos de la instancia con los usuarios y tokens más recientes """
