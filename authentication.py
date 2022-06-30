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

import sys
import os
import string
import json
import logging
import random
import uuid

from service_announcement import ServiceAnnouncementsListener
from service_announcement import ServiceAnnouncementsSender
from server import Services

import Ice # pylint: disable=import-error,wrong-import-position
import IceStorm
Ice.loadSlice('IceFlix.ice')
import IceFlix # pylint: disable=import-error,wrong-import-position

DEFAULT_TOPICMANAGER_PROXY = 'IceStorm/TopicManager:tcp -p 10000'

USERS_FILE = "users.json"

main_proxy = None

# pylint: enable=C0413

TOKEN_SIZE = 30

class Authenticator(IceFlix.Authenticator): # pylint: disable=too-many-instance-attributes

    """ Actúa como servidor de autenticación """

    def __init__(self, comm):

        self._users_ = USERS_FILE
        self.users = IceFlix.UsersDB()
        self.active_tokens = {}
        self.service_id = str(uuid.uuid4())
        self.services = Services()
        self.comm = comm
        self.updatePublisher = self.user_update_subscripcion()
        self.revokePublisher = self.user_revocations_subscripcion()
        self.ServiceAnnouncementsListener = None

        if os.path.exists(USERS_FILE):
            self.refresh()  # Cargar los usuarios
        else:
            self.commitChanges()  # Recargar los cambios realizados sobre el almacén de datos

    def user_update_subscripcion(self): # pylint: disable=missing-function-docstring

        adapter = self.comm.createObjectAdapter("UserUpdatesAdapter")
        adapter.activate()
        proxy = self.comm.stringToProxy(DEFAULT_TOPICMANAGER_PROXY)
        topic_manager = IceStorm.TopicManagerPrx.checkedCast(proxy) # pylint: disable=no-member
        if not topic_manager:
            raise ValueError(f"Proxy {proxy} no válido para TopicManager()")
        try:
            topic = topic_manager.retrieve("user_updates")
        except IceStorm.NoSuchTopic: # pylint: disable=no-member
            topic = topic_manager.create("user_updates")
        update_subscriber = UserUpdates()
        update_subscriber_proxy = adapter.addWithUUID(update_subscriber)
        topic.subscribeAndGetPublisher({}, update_subscriber_proxy)
        update_publisher = topic.getPublisher()
        update_publicador = IceFlix.UserUpdatesPrx.uncheckedCast(update_publisher)
        return update_publicador

    def user_revocations_subscripcion(self): # pylint: disable=missing-function-docstring

        adapter = self.comm.createObjectAdapter("RevocationsAdapter")
        adapter.activate()
        proxy = self.comm.stringToProxy(DEFAULT_TOPICMANAGER_PROXY)
        topic_manager = IceStorm.TopicManagerPrx.checkedCast(proxy) # pylint: disable=no-member
        if not topic_manager:
            raise ValueError(f"Proxy {proxy} no válido para TopicManager()")
        try:
            topic = topic_manager.retrieve("user_revocations")
        except IceStorm.NoSuchTopic: # pylint: disable=no-member
            topic = topic_manager.create("user_revocations")
        revoke_subscriber = Revocations()
        revoke_subscriber_proxy = adapter.addWithUUID(revoke_subscriber)
        topic.subscribeAndGetPublisher({}, revoke_subscriber_proxy)
        revoke_publisher = topic.getPublisher()
        revoke_publicador = IceFlix.RevocationsPrx.uncheckedCast(revoke_publisher)
        return revoke_publicador

    def build_new_token(self):

        """ Construye un nuevo token """

        return "".join(
            [
                random.choice(string.digits + string.ascii_letters)
                for _ in range(TOKEN_SIZE)
            ]
        )

    def refresh(self):

        """ Recarga los datos de los usuarios y sus tokens """

        logging.debug('Cargando los usuarios')
        with open(USERS_FILE, 'r') as contents:  # Abrir el archivo json en modo lectura pylint: disable=unspecified-encoding
            self.users = json.load(contents)  # Cargar el contenido del json en users

    def commitChanges(self):

        """ Recarga los posibles cambios realizados sobre el almacén de datos """

        logging.debug('Actualizando el almacén de datos')
        with open(USERS_FILE, 'w') as contents:  # Abrir el archivo json en modo escritura pylint: disable=unspecified-encoding
            json.dump(self.users, contents)  # Serializar los usuarios en el archivo contents, con indentación 4 y ordenados por su clave

    def refreshAuthorization(self, user, password_hash, current = None): # pylint: disable=invalid-name, unused-argument

        """ Crea un nuevo token de autorización de usuario si las credenciales son válidas """

        logging.debug(f'Nuevo token solicitado por {user}') #pylint: disable=logging-fstring-interpolation
        password = password_hash
        with open(USERS_FILE) as file: #pylint: disable=unspecified-encoding
            data = json.load(file)
            for name in data['users']:
                if user == name["user"] and password == name["password"]:
                    self.active_tokens[name["user"]] = self.build_new_token()
                    self.updatePublisher.newToken(user, self.active_tokens[name["user"]], self.service_id)
                    return self.active_tokens[name["user"]]
            raise IceFlix.Unauthorized()

    def isAuthorized(self, token, current = None): # pylint: disable=invalid-name, unused-argument

        """ Indica si un token dado es válido o no """

        return True if token in self.active_tokens.values() else False  # Comprobar si el token de un usuario se encuentra entre los tokens activos

    def whois(self, token, current = None): # pylint: disable=invalid-name, unused-argument

        """ Permite descubrir el nombre del usuario a partir de un token válido """

        for value in self.active_tokens:
            if token == self.active_tokens[value]:
                return value  # Devolver el nombre de usuario correspondiente al token
        raise IceFlix.Unauthorized

    def addUser(self, user, password_hash, admin, current = None): # pylint: disable=invalid-name, unused-argument

        """ Permite añadir unas nuevas credenciales en el almacén de datos si el token administrativo es correcto """

        check = False
        with open(USERS_FILE) as file: #pylint: disable=unspecified-encoding
            data = json.load(file)
            for name in data['users']:
                if user == name["user"]:
                    print(f'El usuario {user} ya existe')
                    check = True
            if not check:
                data['users'].append({"user": user, "password": password_hash})
        with open(USERS_FILE, "w") as file: #pylint: disable=unspecified-encoding
            json.dump(data, file, indent = 4)
            self.updatePublisher.newUser(user, password_hash, self.service_id)

    def removeUser(self, user, admin, current = None): # pylint: disable=invalid-name, unused-argument

        """ Permite eliminar unas credenciales del almacén de datos si el token administrativo es correcto """

        with open(USERS_FILE) as file: #pylint: disable=unspecified-encoding
            data = json.load(file)
        for indice in range(len(data["users"])):
            if data["users"][indice - 1]["user"] == user:
                del data["users"][indice - 1]
                print("\nUSUARIO eliminado correctamente")
        with open(USERS_FILE, "w") as file: #pylint: disable=unspecified-encoding
            json.dump(data, file, indent = 4)
            self.revokePublisher.revokeUser(user, self.service_id)

    def updateDB(self, valuesDB, service_id, current = None): # pylint: disable=invalid-name, unused-argument

        """ Actualiza la base de datos de la instancia con los usuarios más recientes """

        print("update DB invocado")
        if service_id != self.service_id:
            for item in valuesDB:
                password = item.users_passwords
                for clave, valor in password.iteritems():
                    with open(USERS_FILE) as file: #pylint: disable=unspecified-encoding
                        data = json.load(file)
                        for name in data['users']:
                            if clave == name["user"]:
                                print(f'El usuario {clave} ya existe')
                                check = True
                        if not check:
                            data['users'].append({"user": clave, "password": valor})
                    with open(USERS_FILE, "w") as file: #pylint: disable=unspecified-encoding
                        json.dump(data, file, indent = 4)
                self.active_tokens = item.users_token

    def share_data_with(self, proxy, current = None): # pylint: disable=missing-function-docstring
        self.updateDB(None, None)

class UserUpdates(IceFlix.UserUpdates):

    """ El servicio de autenticación recibe nuevos datos o actualizaciones a los ya existentes """

    def newUser(self, user, password_hash, service_id, current = None): # pylint: disable=invalid-name, unused-argument

        """ Se emite cuando un nuevo usuario es creado por el administrador """

        print("\nEvento NEW USER lanzado")
        check = False
        with open(USERS_FILE) as file: #pylint: disable=unspecified-encoding
            data = json.load(file)
            for name in data['users']:
                if user == name["user"]:
                    check = True
            if not check:
                data['users'].append({"user": user, "password": password_hash})
        with open(USERS_FILE, "w") as file: #pylint: disable=unspecified-encoding
            json.dump(data, file, indent = 4)

    def newToken(self, user, new_token, service_id, current = None): # pylint: disable=invalid-name, unused-argument

        """ Se emite cuando un usuario llama satisfactoriamente a la función refreshAuthorization y un nuevo token es generado """

        print("\nEvento NEW TOKEN lanzado")
        self.active_tokens[user["user"]] = new_token

class Revocations(IceFlix.Revocations):
    """ Recibe datos a eliminar para un usuario """

    def revokeUser(self, user, service_id, current = None): # pylint: disable=invalid-name, unused-argument

        """ Se emite cuando el administrador elimina un usuario del sistema """

        print("\nEvento REVOKE USER lanzado")
        with open(USERS_FILE) as file: #pylint: disable=unspecified-encoding
            data = json.load(file)
        for indice in range(len(data["users"])):
            if data["users"][indice - 1]["user"] == user:
                del data["users"][indice - 1]
        with open(USERS_FILE, "w") as file: #pylint: disable=unspecified-encoding
            json.dump(data, file, indent = 4)

    def revokeToken(self, token, service_id, current = None): # pylint: disable=invalid-name, unused-argument

        """ Se emite cuando un token expira pasados los 2 minutos de validez """

        print("\nEvento REVOKE TOKEN lanzado")
        self.active_tokens[service_id["user"]] = token

class AuthenticatorApp(Ice.Application):

    """ Example Ice.Application for a Authenticator service """

    def __init__(self):

        super().__init__()
        self.proxy = None
        self.adapter = None
        self.announcer = None
        self.subscriber = None

    def setup_announcements(self): # pylint: disable=invalid-name, unused-argument

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
            self.servant, self.servant.service_id, IceFlix.AuthenticatorPrx
        )
        subscriber_prx = self.adapter.addWithUUID(self.subscriber)
        topic.subscribeAndGetPublisher({}, subscriber_prx)

    def run(self, args): # pylint: disable=invalid-name, unused-argument

        """ Run the application, adding the needed objects to the adapter """

        logging.info("Running Authenticator application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("Authentication")
        self.adapter.activate()
        self.servant = Authenticator(comm) #pylint: disable=attribute-defined-outside-init
        self.proxy = self.adapter.addWithUUID(self.servant)
        self.setup_announcements()
        self.announcer.start_service()
        self.shutdownOnInterrupt()
        comm.waitForShutdown()
        self.announcer.stop()
        return 0


if __name__ == "__main__":
    sys.exit(AuthenticatorApp().main(sys.argv))
    