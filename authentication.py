"""Module containing a template for a athentication service."""
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


import os
import string
import json
import logging
import random
import threading

from service_announcement import ServiceAnnouncementsListener
from service_announcement import ServiceAnnouncementsSender
from server import Services

import Ice
Ice.loadSlice('IceFlix.ice')
import IceFlix

DEFAULT_TOPICMANAGER_PROXY = 'IceStorm/TopicManager:tcp -p 10000'

USERS_FILE = 'users.json'

# pylint: enable=C0413

TOKEN_SIZE = 30

TOPIC_MANAGER_PROXY = 'IceStorm/TopicManager:tcp -p 10000'

def build_new_token():

    """ Construye un nuevo token """
    
    letters_digits = string.ascii_letters + string.digits  # Letras mayúsculas (A-Z), minúsculas (a-z) y números (0-9)
    token = ''.join([random.choice(letters_digits) for _ in range(TOKEN_SIZE)])  # Seleccionando aleatoriamente, crear string de longitud 30
   
    return token


class Authenticator(IceFlix.Authenticator):

    """ Actúa como servidor de autenticación """

    def __init__(self):

        self._users_ = USERS_FILE
        self.users = IceFlix.UsersDB()
        self.active_tokens = {}
        self.service_id = None
        self.services = Services()
        self.updatePublisher = None
        self.revocationsPublisher = None
        self.ServiceAnnouncementsListener = None

        if os.path.exists(USERS_FILE): 
            self.refresh()  # Cargar los usuarios
            
        else:
            self.commitChanges()  # Recargar los cambios realizados sobre el almacén de datos

    def refresh(self):
        
        """ Recarga los datos de los usuarios y sus tokens """

        logging.debug('Cargando los usuarios')
        
        with open(USERS_FILE, 'r') as contents:  # Abrir el archivo json en modo lectura
            self.users = json.load(contents)  # Cargar el contenido del json en users

    def commitChanges(self):

        """ Recarga los posibles cambios realizados sobre el almacén de datos """

        logging.debug('Actualizando el almacén de datos')
        
        with open(USERS_FILE, 'w') as contents:  # Abrir el archivo json en modo escritura
            json.dump(self.users, contents)  # Serializar los usuarios en el archivo contents, con indentación 4 y ordenados por su clave

    def refreshAuthorization(self, user, password_hash, current = None):

        """ Crea un nuevo token de autorización de usuario si las credenciales son válidas """

        logging.debug(f'Nuevo token solicitado por {user}')
        
        if user not in self.users:  # Si no se encuentra el usuario
            raise IceFlix.Unauthorized()

        current_hash = self.users[user].values()  # Obtener la contraseña actual del usuario

        if not current_hash:  # Si la contraseña del usuario se encuentra vacía
            raise IceFlix.Unauthorized()

        if current_hash != password_hash:  # Si las contraseñas no coinciden
            raise IceFlix.Unauthorized()

        current_token = self.active_tokens[user]  # Obtener el token actual del usuario
        
        if current_token:  # Si el token existe
                self.active_tokens.pop(current_token)  # Lo eliminamos de los tokens activos
        
        new_token = build_new_token()  # Construimos el nuevo token

        self.updatePublisher.newToken(user, new_token, self.service_id)  # Añadimos el nuevo token

        return new_token

    def isAuthorized(self, user, current = None):

        """ Indica si un token dado es válido o no """

        return True if user in self.active_tokens.keys() else False  # Comprobar si el token de un usuario se encuentra entre los tokens activos

    def whois(self, token, current = None):

        """ Permite descubrir el nombre del usuario a partir de un token válido """

        if token not in self.active_tokens.keys():  # Si el token no existe entre los tokens de los usuarios
            raise IceFlix.Unauthorized

        return self.active_tokens[token]  # Devolver el nombre de usuario correspondiente al token

    def addUser(self, user, password_hash, admin, current = None):

        """ Permite añadir unas nuevas credenciales en el almacén de datos si el token administrativo es correcto """

        active = False
        while active is False:
            if self.services.mainServices != {}:
            
                randomMain = random.choice(list(self.services.mainServices.values()))   # Seleccionar un aleatorio del diccionario
                
                try:
                    randomMain.ice_ping()  # Comprobar que el objeto existe y recibe mensajes
                    active = True
                    
                except:
                    del self.services.mainServices[randomMain]  # Eliminar el objeto randomMain del diccionario
            
            else:
                active = True
                raise IceFlix.TemporaryUnavailable

        checked = IceFlix.MainPrx.checkedCast(randomMain)  # Si el servidor está asociado a la interfaz devuelve el proxy, sino None
        
        if checked.isAdmin(admin):  # Si el token administrativo es correcto
            self.updatePublisher.newUser(user, password_hash, self.service_id)  # Crear el nuevo usuario en el almacén de datos
            
        else:
            raise IceFlix.Unauthorized

    def removeUser(self, user, admin, current = None):

        """ Permite eliminar unas credenciales del almacén de datos si el token administrativo es correcto """

        active = False
        while active is False:
            if self.services.mainServices != {}:
                
                randomMain = random.choice(list(self.services.mainServices.values()))  # Seleccionar un aleatorio del diccionario
                
                try:
                    randomMain.ice_ping()  # Comprobar que el objeto existe y recibe mensajes
                    active = True
                    
                except:
                    del self.services.mainServices[randomMain]   # Eliminar el objeto randomMain del diccionario
            
            else:
                active = True
                raise IceFlix.TemporaryUnavailable
        
        checked = IceFlix.MainPrx.checkedCast(randomMain)  # Si el servidor está asociado a la interfaz devuelve el proxy, sino None
        
        if checked.isAdmin(admin):  # Si el token administrativo es correcto
            self.revocationsPublisher.revokeUser(user, self.service_id)  # Eliminar el usuario del almacén de datos
        
        else:
            raise IceFlix.Unauthorized
        

    def updateDB(self, valuesDB, service_id, current = None):

        """ Actualiza la base de datos de la instancia con los usuarios más recientes """

        logging.info("Recopilando la base de datos de %s para %s", service_id, self.service_id)

        if self.ServiceAnnouncementsListener.validService_id(service_id, "Authenticator"):  # Si el servicio corresponde al Authenticator
            self.users = valuesDB  # Actualizar los usuarios
            print(self.users)
        
        else:
            print("Error al obtener la base de datos")


class UserUpdates(IceFlix.UserUpdates):
    
    """ El servicio de autenticación recibe nuevos datos o actualizaciones a los ya existentes """
    
    def __init__(self):
        
        self.ServiceAnnouncementsListener = None
        self.servant = None
    
    def newUser(self, user, password_hash, service_id, current = None):
        
        """ Se emite cuando un nuevo usuario es creado por el administrador """
        
        if self.ServiceAnnouncementsListener.validService_id(service_id, "Authenticator" ):  # Validar el id comprobando que sea Authenticator
            self.servant.users[user] = password_hash # Establecer los datos del usuario
            self.servant.commitChanges()  # Actualizar los cambios
        
        else:
            print("El origen no corresponde al Authenticator")
        
    def newToken(self, user, new_token, service_id, current = None):
        
        """ Se emite cuando un usuario llama satisfactoriamente a la función refreshAuthorization y un nuevo token es generado """
        
        if self.ServiceAnnouncementsListener.validService_id(service_id, "Authenticator" ):  # Validar el id comprobando que sea Authenticator
            self.servant.active_tokens[user] = new_token  # Establecer el token del usuario
            time = threading.Timer(120, self.servant.revocationsPublisher.revokeToken, [user, service_id]) # Eliminar el token del usuario pasados 2 minutos
            time.start()
            
            print(self.servant.users)  # Mostrar los datos de los usuarios
            
        else:
            print("El origen no corresponde al Authenticator")


class Revocations(IceFlix.Revocations):
    
    """ Recibe datos a eliminar para un usuario """

    def __init__(self):
        
        self.servant = None
        self.ServiceAnnouncementListener = None
        
    def revokeUser(self, user, service_id, current = None):
        
        """ Se emite cuando el administrador elimina un usuario del sistema """
        
        if self.ServiceAnnouncementListener.validService_id(service_id, "Authenticator"):    # Validar el id comprobando que sea Authenticator
            
            if user in self.servant.users:  # Si el usuario existe
                del self.servant.users[user]  # Eliminar el usuario
            self.servant.commitChanges()  # Actualizar los cambios
            
        else:
            print("El origen no corresponde al Authenticator")

    def revokeToken(self, user, service_id, current = None):
        
        """ Se emite cuando un token expira pasados los 2 minutos de validez """
        
        if self.ServiceAnnouncementListener.validService_id(service_id, "Authenticator"):  # Validar el id comprobando que sea Authenticator
            
            if user in self.servant.users:  # Si el usuario existe
                token = self.servant.active_tokens[user]  # Obtener el token del usuario
                del token  # Eliminar el token del usuario
                
            print(self.servant.users)  # Mostrar los datos de los usuarios
            
        else:
            print("El origen no corresponde al Authenticator")


class AuthenticatorApp(Ice.Application):
    
    """ Example Ice.Application for a Main service """

    def __init__(self):
        super().__init__()
        self.servant = Authenticator()
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
            self.servant, self.servant.service_id, IceFlix.AuthPrx
        )

        subscriber_prx = self.adapter.addWithUUID(self.subscriber)
        topic.subscribeAndGetPublisher({}, subscriber_prx)

    def run(self, args):
        
        """ Run the application, adding the needed objects to the adapter """
        
        logging.info("Running Authenticator application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("Authenticator")
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)

        self.setup_announcements()
        self.announcer.start_service()

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        self.announcer.stop()
        return 0