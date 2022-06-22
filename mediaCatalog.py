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

Ice.loadSlice('IceFlix.ice')
import IceFlix
from authentication import Authenticator
from server import Services

CATALOG_FILE = 'catalog.json'

def read_tags_db():
    
    """ Carga la base de datos """
    
    with open(CATALOG_FILE, 'r') as contents:  # Abrir el archivo json en modo lectura
        tags = json.load(contents)  # Cargar el contenido del json en tags
        
    return tags


def write_tags_db(tags):
    
    """ Escribe las tags en la base de datos """
    
    with open(CATALOG_FILE, 'w') as file:
        json.dump(tags, file)
        file.close()


class Catalog(IceFlix.MediaCatalog):
    
    def __init__(self):
        
        """ Inicializar el Catálogo """
        
        self.service_id = str(uuid.uuid4())
        self.catalog = CatalogDB(self.service_id + '.db')
        self.tags_db = 'tags_' + self.service_id + '.json'
        self.services = Services()
        self.proxy = {}
        self.updateSubscriber = None
    
    def getTile(self, media_id, token, current=None):
        
        """ Permite realizar la búsqueda de un medio conocido su identificador """
        
        try:
            user = Authenticator.whois(token)  # Descubirir el nombre de usuario a partir de su token
            
        except IceFlix.Unauthorized:
            user = 'NOT_FOUND'
        
        if not self.catalog.in_catalog(media_id):  # Si no se localiza el id del medio
            raise IceFlix.WrongMediaId(media_id)

        if media_id not in self.proxy:  #Si no existe el proxy
            raise IceFlix.TemporaryUnavailable

        tags_db = read_tags_db()  # Leer las etiquetas de la base de datos

        for user in tags_db:  #Recorrer las tags
            
            if media_id in tags_db[user]:  # Si el id del medio se encuentra entre las etiquetas del usuario
                tags_list = [tag for tag in tags_db[user][media_id]]  # guardar las etiquetas para ese medio y ese usuario
        
        checked = Media(media_id, self.proxy[media_id][-1], MediaInfo(self.catalog.get_name_by_id(media_id), tags_list))
        return checked
    
    def getTilesByName(self, name, exact, current=None):
        
        """ Permite realizar una búsqueda de medios usando su nombre """
        
        tiles = self.catalog.get_id_by_name(name, exact)  # Localizar el id del medio por su nombre
        return tiles
    
    def getTilesByTags(self, tags, AllTags, token, current=None):
        
        """ Permite realizar búsquedas de medios en función de los tags definidos por el usuario """
        
        try:
            user = Authenticator.whois(token)  # Descubirir el nombre de usuario a partir de su token
            
        except IceFlix.Unauthorized:
            user = 'NOT_FOUND'

        tags_db = read_tags_db()  # Leer las etiquetas de la base de datos
        
        if user in tags_db:  # Si el usuario contiene las tags
            tiles_list = []
            
            for media in tags_db[user]:  # Recorrer las tags del usuario
                
                if not AllTags and any(tag in tags_db[user][media] for tag in tags):
                    tiles_list.append(media)
                    
                elif AllTags and all([(tag in tags) for tag in tags_db[user][media]]):
                    tiles_list.append(media)

        return tiles_list

    def addTags(self, media_id, tags, token, current=None): # pylint: disable=invalid-name, unused-argument
        
        """ Permite añadir una lista de tags a un medio concreto """
       
        try:
            user = Authenticator.whois(token)  # Descubirir el nombre de usuario a partir de su token
        
        except IceFlix.Unauthorized:
            user = 'NOT_FOUND'

        if not self.catalog.in_catalog(media_id):  # Si no se localiza el id del medio
            raise IceFlix.WrongMediaId(media_id)

        tags_db = read_tags_db()  # Leer las etiquetas de la base de datos

        if user in tags_db and media_id in tags_db[user]:  # Si el usuario contiene las tags y el medio contiene las tags del usuario
            for tag in tags:  # Recorrer las tags
                tags_db[user][media_id].append(tag)  # Añadir la tag correspondiente al usuario y al medio
                
        elif user in tags_db:  # Si solo el usuario contiene las tags
            tags_db[user][media_id] = tags  # Añadir las tags al usuario y al medio
            
        else:  # Si no
            tags_list = {}
            tags_list[media_id] = tags  # Añadimos las etiqueta al medio
            tags_db[user] = tags_list  # Añadimos las etiquetas del medio al usuario

        write_tags_db(tags_db)
        self.updateSubscriber.publisher.addTags(media_id, tags, user, self.service_id)


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