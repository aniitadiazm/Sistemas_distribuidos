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

from sqlalchemy import false
import Ice
import json
import os
import sqlite3
import random
import logging
import IceStorm
Ice.loadSlice('IceFlix.ice')
import IceFlix
from authentication import Authenticator
from server import Services
from service_announcement import ServiceAnnouncementsListener
from service_announcement import ServiceAnnouncementsSender

CATALOG_FILE = 'catalog.json'
TAGS_FILE = 'tags.json'

MEDIA_NAME = 'name'


class MediaCatalog(IceFlix.MediaCatalog):
    
    def __init__(self):
        
        """ Inicializar el Catálogo """
        
        self._tags_ = TAGS_FILE
        self._catalog_ = CATALOG_FILE
        self.catalog = IceFlix.MediaDB()
        self.tags = IceFlix.MediaDB()
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
        
        if media_id not in self.catalog:  # Si no se localiza el id del medio
            raise IceFlix.TemporaryUnavailable()

        for media_id in self.catalog:  #Recorrer las tags
            
            if media_id in self.catalog:  # Si el id del medio se encuentra entre el catálogo
                name = self.catalog[media_id].get(MEDIA_NAME, None)  # obtener el título del medio correspondiente a ese identificador
        
        return name
    
    def getTilesByName(self, name, exact, current=None):
        
        """ Permite realizar una búsqueda de medios usando su nombre """
        
        exact = false
        tiles_list = []
        for media in self.catalog:  #Recorrer el catálogo 
                name_media = self.catalog[media].get(MEDIA_NAME, None)  # obtener el nombre del medio correspondiente a cada identificador
                
                if name_media == name:
                    tiles_list.append(self.catalog[media].get(MEDIA_NAME, None))  # Añadir el medio a la lista
                    exact = True
                
                if name_media.find(name):  # Si el nombre contiene el nombre de la búsqueda
                    tiles_list.append(self.catalog[media].get(MEDIA_NAME, None))  # Añadir el medio a la lista
                    exact = False
        
        print(f'exact =  {exact}')
        return tiles_list
    
    def getTilesByTags(self, tags_search, inludeAllTags, token, current=None):
        
        """ Permite realizar búsquedas de medios en función de los tags definidos por el usuario """
        
        main_service = self.services.getMainService()
        user = main_service.getAuthenticator().whois(token)
        
        medias_list = []
        tiles_list = []
        counter = 0
        
        for tag in self.tags[user]:  # Recorrer las tags del usuario
            
            for tag_search in tags_search:  # Recorrer las tags a buscar
                
                if tag == tag_search:  # Si las etiquetas coindicen
                    
                    counter = counter + 1
                    
                    for id_media in self.tags[user][tag]: # Recorrer los medios de ese user y tag
                        medias_list.append(id_media) # Añadir a la lista los medios
        
        for id_media_catalog in self.catalog:  # Recorrer la lista de los medios del catalogo
            
            for id_media in medias_list:  # Recorrer la lista de los medios del usuario con esas etiquetas
                
                if id_media == id_media_catalog:  # Si los ids coinciden
                    tiles_list.append(self.catalog[id_media_catalog]).get(MEDIA_NAME, None)  # Guardar el titulo del medio en la lista
        
        if counter == len(tags_search):  # Si el usuario tiene todas las tags buscadas
            includeAllTags = True
        
        print(f'includeAllTags =  {includeAllTags}')
        return tiles_list

    def addTags(self, media_id, tags, token, current=None): # pylint: disable=invalid-name, unused-argument
        
        """ Permite añadir una lista de tags a un medio concreto """
       
    
    def renameTile(self, media_id, name, token, current=None): # pylint: disable=invalid-name, unused-argument
        
        '''Renombra un medio.'''
        
        
    
    def updateDB(self, valuesDB, service_id, current = None):

        """ Actualiza la base de datos de la instancia con los usuarios y tokens más recientes """

        


class CatalogDB():
    
    def __init__(self, database):
        
        self.database = database
        
    def build_connection(self, database):  # pylint: disable=no-self-use
        
        """ Contruye la conexión a la base de datos del catálogo """
        
        connection = sqlite3.connect(database)  # Acceder a la base de datos
        connection.row_factory = lambda cursor, row: row[0]
        return connection
    
    def in_catalog(self, media_id):
        
        """ Comprueba que un objeto media se encuentra en el catálogo """
        
        sql = f"SELECT * FROM catalog WHERE EXISTS (SELECT 1 FROM catalog WHERE id = '{media_id}');"
        result = False
            
        with self.build_connection(self.database) as connection:  # Conectarse a la base de datos
            cursor = connection.cursor()  # Crear un objeto de cursor
            cursor.execute(sql)  # Ejecutar la consulta
            
            if cursor.fetchone():  # Si la consulta devuelve filas como resultado
                result = True
                
        connection.close()
        return result

    def get_name_by_id(self, media_id):
        
        """ Obtiene el nombre de un objeto media a través de su id """
        
        get_by_name_sql = f"SELECT Name FROM catalog WHERE id = '{media_id}';"
        
        with self.build_connection(self.database) as connection:  # Conectarse a la base de datos
            cursor = connection.cursor()  # Crear un objeto de cursor 
            cursor.execute(get_by_name_sql)  # Ejecutar la consulta
            result = cursor.fetchone()  # Guardar las filas que lance como resultado
            
        return result
    
    def get_id_by_name(self, name, exact):
        
        """ Obtiene el id de un objeto media a través de su nombre """
        
        if exact:
            get_id_sql = f"SELECT id FROM catalog WHERE Name='{name}' COLLATE NOCASE"

        else:
            get_id_sql = f"SELECT id FROM catalog WHERE Name LIKE '%{name}%' COLLATE NOCASE"

        with self.build_connection(self.database) as connection:  # Conectarse a la base de datos
            cursor = connection.cursor()  # Crear un objeto de cursor
            cursor.execute(get_id_sql)  # Ejecutar la consulta
            result = cursor.fetchall()  # Guardar las filas que lance como resultado
            
        return result

    def rename_media(self, name, media_id):
        
        """ Renombrar un objeto media del catálogo mediante su id"""
        
        rename_media_sql = f"UPDATE catalog SET Name='{name}' WHERE id='{media_id}'"
        
        with self.build_connection(self.database) as connection:  # Conectarse a la base de datos
            cursor = connection.cursor()  # Crear un objeto de cursor
            cursor.execute(rename_media_sql)  # Ejecutar la consulta
            connection.commit()  # Modificar los datos de la base de datos
            
        connection.close()


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
            
            if media_id not in self.tags:  # Si no se encuentra el usuario
                raise IceFlix.Unauthorized()
            
            self.servant.catalog.rename_media(media_id, name)  # Renombrar el medio a través de su id
        
        else:
            print("El origen no corresponde al MediaCatalog")
        
    def addTags(self, media_id, tags, user, service_id, current=None):
        
        """ Se emite cuando un usuario añade satisfactoriamente tags a algún medio """
        
        if self.ServiceAnnouncementsListener.validService_id(service_id, "MediaCatalog"):  # Si los ids de los servicios coinciden o el medio no se encuentra en el catálogo

            tags_db = read_tags_db()  # Leer las etiquetas de la base de datos

            if user in tags_db and media_id in tags_db[user]:  # Si el usuario contiene las tags y el medio contiene las tags del usuario 
                for tag in tags:  # Recorrer las etiquetas
                    tags_db[user][media_id].append(tag)  # para cada usuario y medio añadir su tag correspondiente
                    
            else:
                tags_list = {}
                tags_list[media_id] = tags # Añadimos las etiquetas al medio
                tags_db[user] = tags_list  # Añadimos las etiquetas del medio al usuario
    
            write_tags_db(tags_db[user])  # Escribir las tags del usuario
        
        else:
            print("El origen no corresponde al MediaCatalog")

    def removeTags(self, media_id, tags, user, service_id, current=None):
         
        """ Se emite cuando un usuario elimina satisfactoriamente tags de algún medio """
        
        if self.ServiceAnnouncementsListener.validService_id(service_id, "MediaCatalog"):  # Si los ids de los servicios coinciden o el medio no se encuentra en el catálogo

            tags_db = read_tags_db()  # Leer las etiquetas de la base de datos
            
            if user in tags_db and media_id in tags_db[user]:  # Si el usuario contiene las tags y el medio contiene las tags del usuario
                tags_db[user][media_id] = [tag for tag in tags_db[user][media_id] if tag not in tags]

            write_tags_db(tags_db)  # Escribir las tags
        
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
    