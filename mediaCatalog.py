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


import json
import os
import logging

import Ice
import IceStorm
Ice.loadSlice('IceFlix.ice')
import IceFlix


from server import Services
from service_announcement import ServiceAnnouncementsListener
from service_announcement import ServiceAnnouncementsSender

CATALOG_FILE = 'catalog.json'
TAGS_FILE = 'tags.json'


class MediaCatalog(IceFlix.MediaCatalog):
    
    def __init__(self):
        
        """ Inicializar el Catálogo """
        
        self._tags_ = TAGS_FILE
        self._catalog_ = CATALOG_FILE
        self.service_id = None
        self.services = Services()
        self.catalogUpdate = None
        self.catalogProvider = {}
        self.mediaProvider = {}
        self.ServiceAnnouncementsListener = None
        
        if os.path.exists(CATALOG_FILE) and os.path.exists(TAGS_FILE): 
            self.refresh()  # Cargar el catálogo y las tags
            
        else:
            self.commitChanges()  # Recargar los cambios realizados sobre el almacén de datos
    
    def refresh(self):
        
        """ Carga el catálogo y las tags """

        logging.debug('Cargando el catálogo y las tags')
        
        with open(CATALOG_FILE, 'r') as contents:  # Abrir el archivo json en modo lectura
            self.catalog = json.load(contents)  # Cargar el contenido del json en catalog
        
        with open(TAGS_FILE, 'r') as contents:  # Abrir el archivo json en modo lectura
            self.tags = json.load(contents)  # Cargar las tags y los medios en tags
     
    def commitChanges(self):

        """ Recarga los posibles cambios realizados sobre el almacén de datos """

        logging.debug('Actualizando el almacén de datos')
        
        with open(CATALOG_FILE, 'w') as contents:  # Abrir el archivo json en modo escritura
            json.dump(self.catalog, contents)  # Serializar el catalog en el archivo contents, con indentación 4 y ordenados por su clave

    def getTile(self, media_id, token, current=None):
        
        """ Permite realizar la búsqueda de un medio conocido su identificador """
        
        object_media = IceFlix.Media()  # Inicializar el objeto media
        object_media_info = IceFlix.MediaInfo()  # Inicializar el objeto media info

        if media_id in self._catalog_:  # Si el medio existe
            name = self._catalog_[media_id]  # Guardar el nombre del medio en name
            object_media.mediaId = media_id  # Asignar el id del medio al objeto media
            object_media_info.name = name  # Asignar el nombre del medio al objeto media info
            object_media.info = object_media_info  # Asignar el objeto media info al objeto media
            print(self.mediaProvider)

            if id in self.mediaProvider:  # Si el medio no tiene proxy asociado
                object_media.provider=self.dicProvider[self.mediaProvider[id]]

            else:
                raise IceFlix.TemporaryUnavailable
        
        else:
            raise IceFlix.WrongMediaId

        return object_media
    
    def getTilesByName(self, name, exact, current=None):
        
        """ Permite realizar una búsqueda de medios usando su nombre """
        
        list_to_return = []

        if exact == True:  # Si el nombre a buscar es exactamente el mismo

            for media in self._catalog_:  # Recorrer el catálogo

                if name.lower() == self._catalog_[media].lower():  # Si los nombres coinciden
                    list_to_return.append(self._catalog_[media])  # Añadir a la lista

        else:  # Si lo que buscamos es parte del nombre de un medio

            for media in self._catalog_:  # Recorrer el catálogo

                if name.lower() in self._catalog_[media].lower():  # Si el nombre contiene lo que se busca
                    list_to_return.append(self._catalog_[media])  # Añadir a la lista
        
        return list_to_return
    
    def getTilesByTags(self, tags_search, inludeAllTags, token, current=None):
        
        """ Permite realizar búsquedas de medios en función de los tags definidos por el usuario """
        
        main_service = self.services.getMainService()
        user = main_service.getAuthenticator().whois(token)
        list_to_return = []
        counter = 0
        check = False

        if includeAllTags is True:
            for media_id in self._tags_:
                if user in self._tags_[media_id]: 
                    for tag in self._tags_[media_id][user]:
                        for tag_search in tags_search:
                            if tag == tag_search:
                                counter = counter+1
                                if counter == len(self._tags_[user]):
                                    list_to_return.append(media_id)

        else:
            for media_id in self._tags_:
                if user in self._tags_[media_id]:
                    for tag in self._tags_[media_id][user]:
                        for tag_search in tags_search:
                            if tag == tag_search:
                                id = media_id
                                for id_search in list_to_return:
                                    if id_search == id:
                                        check = True
                                if check == False:
                                    list_to_return.append(media_id)

        return list_to_return

    def addTags(self, media_id, tags, token, current=None): # pylint: disable=invalid-name, unused-argument
        
        """ Permite añadir una lista de tags a un medio concreto """

        main_service = self.services.getMainService()
        user = main_service.getAuthenticator().whois(token)  # Obtener el nombre de usuario

        check = False

        for media in self._tags_:  # Recorrer los medios
            if self._tags_[media] == media_id:  # Si se localiza el id del medio
                check = True
        
        if check == False:
            raise IceFlix.WrongMediaId  # Si no se localiza el id del medio salta excepción

        self.catalogUpdate.addTags(media_id, tags, user, self.service_id)  # Añadir las etiquetas al medio y al usuario
    
    def renameTile(self, media_id, name, token, current=None): # pylint: disable=invalid-name, unused-argument
        
        """ Operación de administración que permite renombrar un determinado medio en la base de datos """
        
        main_service = self.se.getMainService()

        if main_service.isAdmin(token):  # Si el token es administrativo

            check = False

            for media in self._catalog_:  # Recorrer los medios
                if media == media_id:  # Si los medios coinciden
                    check = True
            
            if check == False:
                raise IceFlix.WrongMediaId  # Si no se localiza el id del medio salta excepción

            self.catalogUpdate.renameTile(media_id, name, self.service_id)  # Renombrar el medio
        
        else:
            raise IceFlix.Unauthorized()  # Si no es admin no está autorizado
    
    def updateDB(self, valuesDB, service_id, current = None):

        """ Actualiza la base de datos de la instancia con los usuarios y tokens más recientes """

        

class Media(IceFlix.Media):
    
    """ Inicializar el objeto Media de IceFlix """
    
    def __init__(self, media_id, provider, info):
        
        self.media_id = media_id
        self.provider = provider
        self.info = info


class MediaInfo(IceFlix.MediaInfo):
    
    """ Inicializar el objeto MediaInfo de IceFlix """
    
    def __init__(self, name, tags):
        
        self.name = name
        self.tags = tags


class CatalogUpdates(IceFlix.CatalogUpdates):
    
    def __init__(self, servant):
        
        self.servant = servant
        self.ServiceAnnouncementsListener = None
        
    def renameTile(self, media_id, name, service_id, current=None):
        
        """ Se emite cuando el administrador modifica el nombre de un medio en una instancia """
        
        if self.ServiceAnnouncementsListener.validService_id(service_id, "MediaCatalog"):  # Si los ids de los servicios coinciden o el medio no se encuentra en el catálogo

            for media in self.servant._catalog_:  # Recorrer los medios
                if media == media_id:  # Si los ids coinciden
                    self.servant._catalog_[media] = name  # Asignar el nuevo nombre al medio

            self.servant.commitChanges()  # Actualizar los cambios

        else:
            print("El origen no corresponde al MediaCatalog")
        
    def addTags(self, media_id, tags, user, service_id, current=None):
        
        """ Se emite cuando un usuario añade satisfactoriamente tags a algún medio """
        
        if self.ServiceAnnouncementsListener.validSrvid(service_id, "MediaCatalog"):  # Si los ids de los servicios coinciden o el medio no se encuentra en el catálogo

            for media in self.servant._tags_:  # Recorrer los medios
                if media == media_id:  # Si los ids coinciden
                    if user not in self.servant._tags_[media]:  # Si el usuario no se encuentra en ese medio
                        self.servant._tags_[media][user] = tags  # Creamos el usuario y añadimos las etiquetas

                    else:  # Si el usuario ya estaba en ese medio
                        for tag in tags:  # Recorrer las etiquetas
                            self.servant._tags_[media][user].append(tag)  # Añadírselas al usuario

            self.servant.commitChanges()  # Actualizar los cambios
        
        else:
            print("El origen no corresponde al MediaCatalog")

    def removeTags(self, media_id, tags, user, service_id, current=None):
         
        """ Se emite cuando un usuario elimina satisfactoriamente tags de algún medio """
        
        if self.ServiceAnnouncementsListener.validService_id(service_id, "MediaCatalog"):  # Si los ids de los servicios coinciden o el medio no se encuentra en el catálogo

            
        
        else:
            print("El origen no corresponde al MediaCatalog")


class MediaCatalogApp(Ice.Application):
    
    """ Example Ice.Application for a MediaCatalog service """

    def __init__(self):
        super().__init__()
        self.servant = MediaCatalog()
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
        
        logging.info("Running MediaCatalog application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("MediaCatalog")
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)

        self.setup_announcements()
        self.announcer.start_service()

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        self.announcer.stop()
        return 0
    