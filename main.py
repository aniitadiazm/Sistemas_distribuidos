"""Module containing a template for a main service."""
#!/usr/bin/python3
# -*- coding: utf-8 -*-

# pylint: disable=C0103
# pylint: disable=C0301
# pylint: disable=C0113
# pylint: disable=E0401
# pylint: disable=C0103
# pylint: disable=C0411
# pylint: disable=C0413
# pylint: disable=W0613

import logging
import random
import sys

from service_announcement import ServiceAnnouncementsListener
from service_announcement import ServiceAnnouncementsSender

import Ice # pylint: disable=import-error,wrong-import-position
import IceStorm
Ice.loadSlice('IceFlix.ice')
import IceFlix # pylint: disable=import-error,wrong-import-position

DEFAULT_TOPICMANAGER_PROXY = 'IceStorm/TopicManager:tcp -p 10000'

TOKEN_ADMIN = "admin"


class Main(IceFlix.Main):

    """ Servant for the IceFlix.Main interface.
    Disclaimer: this is demo code, it lacks of most of the needed methods
    for this interface. Use it with caution """

    def __init__(self):

        """ Create the Main servant instance """

        self.service_id = None
        self.ServiceAnnouncementsListener = None
        self.volatileServices = IceFlix.VolatileServices()

    def share_data_with(self, service):

        """ Share the current database with an incoming service """

        service.updateDB(None, self.service_id)

    def updateDB(self, values, service_id, current = None):  # pylint: disable=invalid-name,unused-argument

        """ Actualiza la base de datos de la instancia con los usuarios y tokens más recientes """

        self.volatileServices.authenticators = values.authenticators.copy()
        print("authenticators")
        print(self.volatileServices.authenticators)

        self.volatileServices.mediaCatalogs = values.mediaCatalogs.copy()
        print("catalogs")
        print(self.volatileServices.mediaCatalogs)

    def isAdmin(self, admin, current = None):

        """ Devuelve un valor booleano para comprobar si el token proporcionado corresponde o no con el administrativo """

        if admin == TOKEN_ADMIN:  # Si el token recibido es administrador
            return True

        return False

    def getAuthenticator(self, current = None):

        """ Devuelve un proxy a un servicio de autenticación """

        active = False
        while active is False:

            if len(self.volatileServices.authenticators) != 0:
                randomAuth = random.choice(self.volatileServices.authenticators)  # Selecciona un aleatorio de la lista

                try:
                    randomAuth.ice_ping()  # Si el objeto existe y se le puede mandar un mensaje

                except: # pylint: disable=bare-except
                    self.volatileServices.authenticators.remove(randomAuth)

            else:
                active = True
                raise IceFlix.TemporaryUnavailable

            return randomAuth

    def getCatalog(self, current=None):

        """ Devuelve un proxy a un servicio de catálogo """

        active = False
        while active is False:

            if self.volatileServices.mediaCatalogs != []:
                randomCatalog = random.choice(self.volatileServices.mediaCatalogs)  # Selecciona un aleatorio de la lista

                try:
                    randomCatalog.ice_ping()  # Comprobar que el objeto existe y recibe mensajes
                    active = True

                except: # pylint: disable=bare-except
                    self.volatileServices.mediaCatalogs.remove(randomCatalog)

            else:
                active = True
                raise IceFlix.TemporaryUnavailable

        checked = IceFlix.MediaCatalogPrx.checkedCast(randomCatalog)  # Si el servidor está asociado a la interfaz devuelve el proxy, sino None
        return checked

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
        proxy = communicator.stringToProxy(DEFAULT_TOPICMANAGER_PROXY)
        topic_manager = IceStorm.TopicManagerPrx.checkedCast(proxy) # pylint: disable=no-member

        try:
            topic = topic_manager.create("ServiceAnnouncements")

        except IceStorm.TopicExists: # pylint: disable=no-member
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
        print(self.proxy, flush = None)

        self.setup_announcements()
        self.announcer.start_service()

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        self.announcer.stop()
        return 0

if __name__ == "__main__":
    sys.exit(MainApp().main(sys.argv))
    