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

import Ice
import json
import uuid
import sqlite3

from authentication import Authenticator
Ice.loadSlice('IceFlix.ice')
import IceFlix
from service_announcement import ServiceAnnouncementsListener
from service_announcement import ServiceAnnouncementsSender
from main import Main
from server import Services

CATALOG_FILE = 'catalog.json'

def read_tags_db():
    
    """ Carga la base de datos """
    
    with open(CATALOG_FILE, 'r') as contents:  # Abrir el archivo json en modo lectura
        tags = json.load(contents)  # Cargar el contenido del json en tags
        
    return tags


class Catalog(IceFlix.MediaCatalog):
    
    def __init__(self):
        
        """ Inicializar el Catálogo """
        
        self.service_id = str(uuid.uuid4())
        self.catalog = CatalogDB(self.service_id + '.db')
        self.tags_db = 'tags_' + self.service_id + '.json'
        self.services = Services()
        self.proxy = {}
    
    def getTile(self, media_id, user, current=None):
        
        """ Permite realizar la búsqueda de un medio conocido su identificador """
        
        if not self.catalog.in_catalog(media_id):
            raise IceFlix.WrongMediaId(media_id)

        if media_id not in self.proxy:
            raise IceFlix.TemporaryUnavailable

        try:
            user = Authenticator.whois(user) 
            
        except IceFlix.Unauthorized:
            user = 'NOT_FOUND'

        tags = read_tags_db()
        tag_list = []

        for user in tags:
            if media_id in tags[user]:
                tag_list = [tag for tag in tags[user][media_id]]
        
        checked = Media(media_id, self.proxy[media_id][-1], MediaInfo(self.catalog.get_name_by_id(media_id), tag_list))
        return checked
    
    def getTilesByName(self, name, exact, current=None):
        
        """ Permite realizar una búsqueda de medios usando su nombre """
        
        tiles = self.catalog.get_id_by_name(name, exact)
        return tiles


class CatalogDB():
    
    def __init__(self, database):
        
        self.database = database
        
    def build_connection(self, database):
        
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


class Media(IceFlix.Media):
    
    """ Inicializar el objeto Media de IceFlix """
    
    def __init__(self, media_id, provider, info):
        
        self.media_id = media_id # pylint: disable=invalid-name
        self.provider = provider
        self.info = info


class MediaInfo(IceFlix.MediaInfo):
    
    """ Inicializar el objeto MediaInfo de IceFlix """
    
    def __init__(self, name, tags):
        
        self.name = name
        self.tags = tags