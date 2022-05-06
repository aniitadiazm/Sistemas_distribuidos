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
TOKEN_SIZE = 40


def build_new_token():

    """ Método para construir un nuevo token """
    
    token = string.ascii_uppercase + string.digits + string.ascii_lowercase
    return ''.join([random.choice(token) for _ in range(TOKEN_SIZE)])


class AuthenticatorInterface(IceFlix.Authenticator):

    """ Clase que actúa como servidor de autenticación """

    def __init__(self):

        self.users = {}
        self.active_tokens = set()

        if os.path.exists(USERS_FILE):
            self.refreshAuthorization()
        else:
            self.commitChanges()

    def refresh(self):
        
        """ Recarga los tokens de los usuarios """

        logging.debug('Reloading user database')
        with open(USERS_FILE, 'r', encoding='utf-8') as contents:
            self.users = json.load(contents)
            self.active_tokens = set([user.get(CURRENT_TOKEN, None) for user in self.users.values()])
            print(self.active_tokens)

    def commitChanges(self):

        """ Recarga los posibles cambios realizados sobre el almacén de datos """

        logging.debug('User database updated')
        with open(USERS_FILE, 'w') as contents:
            json.dump(self.users, contents, indent=4, sort_keys=True)

    def refreshAuthorization(self, user, passwordHash, current=None):

        """ Crea un nuevo token de autorización de usuario si las credenciales son válidas """

        logging.debug(f'New token requested by {user}')
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

    def isAuthorized(self, userToken, current=None):

        """ Indica si un token dado es válido o no """

        return True if userToken in self.active_tokens else False

    def whois(self, userToken, current=None):

        """ Permite descubrir el nombre del usuario a partir de un token válido """

        if userToken not in self.users.usersToken:
            raise IceFlix.Unauthorized

        return users.usersToken[userToken]

    def addUser(self, username, passwordHash, adminToken, current=None):

        """ Permite añadir unas nuevas credenciales en el almacén de datos
        si el token administrativo es correcto """



    def removeUser(self, username, adminToken, current=None):

        """ Permite eliminar unas credenciales del almacén de datos
        si el token administrativo es correcto """

        

    def updateDB(self, currentDataBase, srvId, current=None):

        """ Actualiza la base de datos de la instancia con los usuarios y tokens más recientes """

