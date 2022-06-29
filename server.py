#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-

# pylint: disable=C0103
# pylint: disable=C0301
# pylint: disable=C0113
# pylint: disable=E0401
# pylint: disable=C0103
# pylint: disable=C0411
# pylint: disable=C0413
# pylint: disable=W0613

import random
import logging

import Ice
import IceStorm
Ice.loadSlice('IceFlix.ice')
import IceFlix

from service_announcement import ServiceAnnouncementsListener
from service_announcement import ServiceAnnouncementsSender


class Services(Ice.Application):
    
    """ Contiene todos los servicios necesarios para ejecutar la aplicación """
    
    def __init__(self):
        
        """ Inicializar todos los microservicios """
                
        super().__init__()
        self.mainServices = {}
        self.authServices = {}
        self.catalogServices = {}
        self.streamServices = {}
        self.service_id = None
    
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


class ServerApp(Ice.Application):

    """ Ice.Application for a Server """

    def __init__(self):
        super().__init__()
        self.servant = Services()
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
        
        logging.info("Running Server application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("Server")
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)
        print(self.proxy, flush = None)

        self.setup_announcements()
        self.announcer.start_service()

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        self.announcer.stop()
        return 0
    


