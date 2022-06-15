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
import Ice
import json
import logging
import random
Ice.loadSlice('IceFlix.ice')
import IceFlix
from service_announcement import ServiceAnnouncementsListener
from server import Services

DEFAULT_TOPICMANAGER_PROXY = 'IceStorm/TopicManager:tcp -p 10000'

USERS_FILE = 'users.json'

# pylint: enable=C0413

CURRENT_TOKEN = 'current_token'
PASSWORD_HASH = 'password_hash'
TOKEN_SIZE = 30


def build_new_token():

    """ Construye un nuevo token """
    
    letters_digits = string.ascii_letters + string.digits  # Letras mayúsculas (A-Z), minúsculas (a-z) y números (0-9)
    token = ''.join([random.choice(letters_digits) for _ in range(TOKEN_SIZE)])  # Seleccionando aleatoriamente, crear string de longitud 30
   
    return token


class Authenticator(IceFlix.Authenticator):

    """ Actúa como servidor de autenticación """

    def __init__(self):

        self.users = {}
        self.active_tokens = set()
        self.service_id = None
        self.services = Services()

        if os.path.exists(USERS_FILE): 
            self.refresh()  # Recargar los tokens
            
        else:
            self.commitChanges()  # Recargar los cambios realizados sobre el almacén de datos

    def refresh(self):
        
        """ Recarga los tokens de los usuarios """

        logging.debug('Cargando los tokens de los usuarios')
        
        with open(USERS_FILE, 'r') as contents:  # Abrir el archivo json en modo lectura
            self.users = json.load(contents)  # Cargar el contenido del json en users
            self.active_tokens = set([user.get(CURRENT_TOKEN, None) for user in self.users.values()])  # Para cada uno de los usuarios, obtener su token

    def commitChanges(self):

        """ Recarga los posibles cambios realizados sobre el almacén de datos """

        logging.debug('Actualizando el almacén de datos')
        
        with open(USERS_FILE, 'w') as contents:  # Abrir el archivo json en modo escritura
            json.dump(self.users, contents, indent = 4, sort_keys = True)  # Serializar los usuarios en el archivo contents, con indentación 4 y ordenados por su clave

    def refreshAuthorization(self, user, passwordHash, current = None):

        """ Crea un nuevo token de autorización de usuario si las credenciales son válidas """

        logging.debug(f'Nuevo token solicitado por {user}')
        
        if user not in self.users:  # Si no se encuentra el usuario
            raise IceFlix.Unauthorized()

        current_hash = self.users[user].get(PASSWORD_HASH, None)  # Obtener la contraseña actual del usuario

        if not current_hash:  # Si el usuario se encuentra vacío
            raise IceFlix.Unauthorized()

        if current_hash != passwordHash:  # Si las contraseñas no coinciden
            raise IceFlix.Unauthorized()

        current_token = self._users_[user].get(CURRENT_TOKEN, None)  # Obtener el token actual del usuario
        
        if current_token:  # Si el token existe
            
                self.active_tokens.remove(current_token)  # Lo eliminamos de entre los tokens activos
        
        new_token = build_new_token()  # Construimos el nuevo token

        self.users[user][CURRENT_TOKEN] = new_token  # Guardamos el token nuevo en el usuario correspondiente
        self.commitChanges()  # Actualizamos los cambios realizados en el almacén de datos
        self.active_tokens.add(new_token)  # Añadimos el token nuevo a los tokens activos

        return new_token

    def isAuthorized(self, userToken, current = None):

        """ Indica si un token dado es válido o no """

        return True if userToken in self.active_tokens else False  # Comprobar si el token se encuentra entre los tokens activos

    def whois(self, userToken, current = None):

        """ Permite descubrir el nombre del usuario a partir de un token válido """

        if userToken not in self.users.usersToken:  # Si el token no existe entre los tokens de los usuarios
            raise IceFlix.Unauthorized

        return self.users.usersToken[userToken]  # Devolver el nombre de usuario correspondiente al token

    def addUser(self, username, passwordHash, adminToken, current = None):

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
        
        if checked.isAdmin(adminToken):  # Si el token administrativo es correcto
            self.userUpdatePublisher.newUser(username, passwordHash, self.service_id)  # Crear el nuevo usuario en el almacén de datos
            
        else:
            raise IceFlix.Unauthorized

    def removeUser(self, username, adminToken, current = None):

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
        
        if checked.isAdmin(adminToken):  # Si el token administrativo es correcto
            self.revocationsPublisher.revokeUser(username, self.service_id)  # Eliminar el usuario del almacén de datos
        
        else:
            raise IceFlix.Unauthorized
        

    def updateDB(self, values, service_id, current = None):

        """ Actualiza la base de datos de la instancia con los usuarios y tokens más recientes """

        logging.info("Recopilando la base de datos de %s para %s", service_id, self.service_id)

        if self.ServiceAnnouncementsListener.validService_id(service_id, "Authenticator"):
            self.users = values
            print(self.users)
        
        else:
            print("Error al obtener la base de datos")


class UserUpdates(IceFlix.UserUpdates):
    
    """ El servicio de autenticación recibe nuevos datos o actualizaciones a los ya existentes """
    
    def __init__(self):
        
        self.ServiceAnnouncements = None
        self.servant = None
    
    def newUser(self, user, passwordHash, service_id, current = None):
        
        """ Recibe nuevos datos o actualizaciones para un usuario """
        
        if self.serviceAnnouncements.validService_id(service_id, "Authenticator" ):  # Validar el id comprobando que sea Authenticator
            self.servant.users.userPasswords[user] = passwordHash  # Recopilar las contraseñas de los usuarios
            self.servant.commitChanges()  # Actualizar los cambios
        
        else:
            print("El origen no corresponde al Authenticator")
        
    def newToken(self, user, userToken, service_id, current = None):
        
        """  Recibe nuevos datos o actualizaciones para un token """
        
        if self.serviceAnnouncements.validService_id(service_id, "Authenticator" ):  # Validar el id comprobando que sea Authenticator
            self.servant.users.usersToken[user] = userToken  # Recopilar los tokens de los usuarios
            print(self.servant.users)  # Actualizar los cambios
            
        else:
            print("El origen no corresponde al Authenticator")