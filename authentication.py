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
import threading
import uuid

from service_announcement import ServiceAnnouncementsListener
from service_announcement import ServiceAnnouncementsSender
from server import Services

import Ice
import IceStorm
Ice.loadSlice('IceFlix.ice')
import IceFlix

DEFAULT_TOPICMANAGER_PROXY = 'IceStorm/TopicManager:tcp -p 10000'

USERS_FILE = "users.json"

main_proxy = None

# pylint: enable=C0413

TOKEN_SIZE = 30



class Authenticator(IceFlix.Authenticator):

    """ Actúa como servidor de autenticación """

    def __init__(self):

        self._users_ = USERS_FILE
        self.users = IceFlix.UsersDB()
        self.active_tokens = {}
        self.service_id = str(uuid.uuid4())
        self.services = Services()
       # self.updatePublisher = self.user_update_subscripcion()
        self.revocationsPublisher = None
        self.ServiceAnnouncementsListener = None
        

        if os.path.exists(USERS_FILE):
            self.refresh()  # Cargar los usuarios
            
        else:
            self.commitChanges()  # Recargar los cambios realizados sobre el almacén de datos
    
    # def user_update_subscripcion(self):

    #     self.adapter = self.broker.createObjectAdapter("UserUpdatesAdapter")
    #     self.adapter.activate()

    #     proxy = self.communicator.stringToProxy(DEFAULT_TOPICMANAGER_PROXY)
    #     topic_manager = IceStorm.TopicManagerPrx.checkedCast(proxy)

    #     if not topic_manager:
    #         raise ValueError(f"Proxy {proxy} no válido para TopicManager()")

    #     try:
    #         topic = topic_manager.retrieve("user_updates")

    #     except IceStorm.NoSuchTopic:
    #         topic = topic_manager.create("user_updates")
     
    #     update_subscriber = UserUpdates()
    #     update_subscriber_proxy = adapter_user_updates.addWithUUID(update_subscriber)
    #     topic.subscribeAndGetPublisher({}, update_subscriber_proxy)
    #     update_publisher = topic.getPublisher()
    #     update_publicador = IceFlix.UserUpdatesPrx.uncheckedCast(update_publisher)

    #     return update_publicador
    
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
        
        with open(USERS_FILE, 'r') as contents:  # Abrir el archivo json en modo lectura
            self.users = json.load(contents)  # Cargar el contenido del json en users

    def commitChanges(self):

        """ Recarga los posibles cambios realizados sobre el almacén de datos """

        logging.debug('Actualizando el almacén de datos')
        
        with open(USERS_FILE, 'w') as contents:  # Abrir el archivo json en modo escritura
            json.dump(self.users, contents)  # Serializar los usuarios en el archivo contents, con indentación 4 y ordenados por su clave

    def refreshAuthorization(self, user, password_hash, current = None):

        """ Crea un nuevo token de autorización de usuario si las credenciales son válidas """
        print("hola")
        logging.debug(f'Nuevo token solicitado por {user}')
        
        password = password_hash
        
        with open(USERS_FILE) as file:
            data = json.load(file)
            
            for name in data['users']:
                
                if user == name["user"] and password == name["password"]:
                    self.active_tokens[name["user"]] = self.build_new_token()

                #   self.updatePublisher.newToken(user, self.active_tokens[key])
                    return self.active_tokens[name["user"]]
            
            raise IceFlix.Unauthorized()
            
    def isAuthorized(self, token, current = None):

        """ Indica si un token dado es válido o no """

        return True if token in self.active_tokens.values() else False  # Comprobar si el token de un usuario se encuentra entre los tokens activos

    def whois(self, token, current = None):

        """ Permite descubrir el nombre del usuario a partir de un token válido """
        
        for value in self.active_tokens:

            if token == self.active_tokens[value]:
                return value  # Devolver el nombre de usuario correspondiente al token
            
        raise IceFlix.Unauthorized

    def addUser(self, user, password_hash, admin, current = None):

        """ Permite añadir unas nuevas credenciales en el almacén de datos si el token administrativo es correcto """
        
        check = False

        with open(USERS_FILE) as file:
            data = json.load(file)

            for name in data['users']:

                if user == name["user"]:
                    print(f'El usuario {user} ya existe')
                    check = True

            if not check:
                data['users'].append({"user": user, "password": password_hash})
        
        with open(USERS_FILE, "w") as file:
            json.dump(data, file, indent = 4)

    def removeUser(self, user, admin, current = None):

        """ Permite eliminar unas credenciales del almacén de datos si el token administrativo es correcto """

        with open(USERS_FILE) as file:
            data = json.load(file)

        for indice in range(len(data["users"])):

                if data["users"][indice - 1]["user"] == user:
                    del data["users"][indice - 1]
        
        with open(USERS_FILE, "w") as file:
            json.dump(data, file, indent = 4)      

    def updateDB(self, valuesDB, service_id, current = None):

        """ Actualiza la base de datos de la instancia con los usuarios más recientes """
        
        logging.info("Recopilando la base de datos de %s para %s", service_id, self.service_id)
        
        if self.ServiceAnnouncementsListener.validService_id(service_id, "Authenticator"):  # Si el servicio corresponde al Authenticator
            self.users = valuesDB  # Actualizar los usuarios
            print(self.users)

        else:
            print("Error al obtener la base de datos")
    
    def share_data_with(self, proxy, current = None):

        self.updateDB(None, None)

# class UserUpdates(IceFlix.UserUpdates):
    
#     """ El servicio de autenticación recibe nuevos datos o actualizaciones a los ya existentes """
 
#     def newUser(self, user, password_hash, service_id, current = None):
        
#         """ Se emite cuando un nuevo usuario es creado por el administrador """
        
#         # if self.ServiceAnnouncementsListener.validService_id(service_id, "Authenticator" ):  # Validar el id comprobando que sea Authenticator
#         #     self.servant.users[user] = password_hash # Establecer los datos del usuario
#         #     self.servant.commitChanges()  # Actualizar los cambios
        
#         # else:
#         #     print("El origen no corresponde al Authenticator")
#         print("new user")
        
#     def newToken(self, user, new_token, service_id, current = None):
        
#         """ Se emite cuando un usuario llama satisfactoriamente a la función refreshAuthorization y un nuevo token es generado """
        
#         if self.ServiceAnnouncementsListener.validService_id(service_id, "Authenticator" ):  # Validar el id comprobando que sea Authenticator
#             self.servant.active_tokens[user] = new_token  # Establecer el token del usuario
#             time = threading.Timer(120, self.servant.revocationsPublisher.revokeToken, [user, service_id]) # Eliminar el token del usuario pasados 2 minutos
#             time.start()
            
#             print(self.servant.users)  # Mostrar los datos de los usuarios
            
#         else:
#             print("El origen no corresponde al Authenticator")
     
    

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
        proxy = communicator.stringToProxy(DEFAULT_TOPICMANAGER_PROXY)
        topic_manager = IceStorm.TopicManagerPrx.checkedCast(proxy)
        
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
            self.servant, self.servant.service_id, IceFlix.AuthenticatorPrx
        )

        subscriber_prx = self.adapter.addWithUUID(self.subscriber)
        topic.subscribeAndGetPublisher({}, subscriber_prx)

    def run(self, args):
        
        """ Run the application, adding the needed objects to the adapter """
        
        logging.info("Running Authenticator application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("Authentication")
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)
        
        self.setup_announcements()
        self.announcer.start_service()

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        self.announcer.stop()
        return 0
    

if __name__ == "__main__":
    sys.exit(AuthenticatorApp().main(sys.argv))