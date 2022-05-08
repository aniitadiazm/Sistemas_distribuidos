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


class AuthenticatorInterface(IceFlix.Authenticator):

    """ Actúa como servidor de autenticación """

    def __init__(self):

        self.users = {}
        self.active_tokens = set()

        if os.path.exists(USERS_FILE): 
            self.refresh()  # Recargar los tokens
            
        else:
            self.commitChanges()  # Recargar los cambios realizados sobre el almacén de datos

    def refresh(self):
        
        """ Recarga los tokens de los usuarios """

        logging.debug('Cargando los tokens de los usuarios')
        
        with open(USERS_FILE, 'r') as contents:
            self.users = json.load(contents)  # Cargar el contenido del json en users
            self.active_tokens = set([user.get(CURRENT_TOKEN, None) for user in self.users.values()])  # Para cada uno de los usuarios, obtener su token

    def commitChanges(self):

        """ Recarga los posibles cambios realizados sobre el almacén de datos """

        logging.debug('Actualizando el almacén de datos')
        
        with open(USERS_FILE, 'w') as contents:
            json.dump(self.users, contents, indent = 4, sort_keys = True)  # Serializar los usuarios en el archivo contents, con indentación 4 y ordenados por su clave

    def refreshAuthorization(self, user, passwordHash, current = None):

        """ Crea un nuevo token de autorización de usuario si las credenciales son válidas """

        logging.debug(f'Nuevo token solicitado por {user}')
        
        if user not in self.users:
            raise IceFlix.Unauthorized()

        current_hash = self.users[user].get(PASSWORD_HASH, None)

        if not current_hash:
            raise IceFlix.Unauthorized()

        if current_hash != passwordHash:
            raise IceFlix.Unauthorized()

        new_token = build_new_token()

        self.users[user][CURRENT_TOKEN] = new_token
        self.commitChanges()
        self.active_tokens.add(new_token)

        return new_token

    def isAuthorized(self, userToken, current = None):

        """ Indica si un token dado es válido o no """

        return True if userToken in self.active_tokens else False

    def whois(self, userToken, current = None):

        """ Permite descubrir el nombre del usuario a partir de un token válido """

        if userToken not in self.users.usersToken:
            raise IceFlix.Unauthorized

        return users.usersToken[userToken]

    def addUser(self, username, passwordHash, adminToken, current = None):

        """ Permite añadir unas nuevas credenciales en el almacén de datos
        si el token administrativo es correcto """

        active = False
        while active is False:
            if self.se.mainServices != {}:
            
                randomMain = random.choice(list(self.se.mainServices.values()))   # Selecciona un aleatorio del diccionario
                
                try:
                    randomMain.ice_ping()  # Comprobar que el objeto existe y recibe mensajes
                    active = True
                    
                except:
                    del self.se.mainServices[randomMain]  # Elimnar el objeto randomMain del diccionario
            
            else:
                active = True
                raise IceFlix.TemporaryUnavailable

        checked = IceFlix.MainPrx.checkedCast(randomMain)  # Si el servidor está asociado a la interfaz devuelve el proxy, sino None
        
        if checked.isAdmin(adminToken):  # Si el token administrativo es correcto
            self.userUpdatePublisher.newUser(username, passwordHash, self.srvId)  # Crear el nuevo usuario en el almacén de datos
            
        else:
            raise IceFlix.Unauthorized

    def removeUser(self, username, adminToken, current = None):

        """ Permite eliminar unas credenciales del almacén de datos
        si el token administrativo es correcto """

        

    def updateDB(self, currentDataBase, srvId, current = None):

        """ Actualiza la base de datos de la instancia con los usuarios y tokens más recientes """

