#!/usr/bin/python3
# -*- coding: utf-8 -*-hashlib

# pylint: disable=C0103
# pylint: disable=C0301
# pylint: disable=C0113
# pylint: disable=E0401
# pylint: disable=C0103
# pylint: disable=C0411
# pylint: disable=C0413
# pylint: disable=W0613

import hashlib
import getpass
import logging
import time
import Ice
import IceStorm
Ice.loadSlice('IceFlix.ice')
import IceFlix


from authentication import Revocations


DEFAULT_TOPICMANAGER_PROXY = 'IceStorm/TopicManager:tcp -p 10000'
     
            
class Cliente():
    
    def __init__(self, token, password_hash, user):
        
        self.token = token
        self.password_hash = password_hash
        self.user = user
        

class Client(Ice.Application):

    def get_topic_manager(self):
        
        proxy = self.communicator().stringToProxy(DEFAULT_TOPICMANAGER_PROXY)
        
        if proxy is None:
            print("\n Propiedad {} no establecida".format(DEFAULT_TOPICMANAGER_PROXY))
            return None

        print("\n Utilizando IceStorm en: '%s'" % DEFAULT_TOPICMANAGER_PROXY)
        
        return IceStorm.TopicManagerPrx.checkedCast(proxy)

    def connectRevocations(self, adapter, topic_Manager, main_Server):
        
        servant_Revocations = Revocations()
        client_Subscriber = adapter.addWithUUID(servant_Revocations)

        topicRe = "Revocations"
        
        try:
            topic_Revocations = topic_Manager.retrieve(topicRe)
            
        except IceStorm.NoSuchTopic:
            print("\n No existe el topic")
            topic_Revocations = topic_Manager.create(topicRe)
        
        topic_Revocations.subscribeAndGetPublisher({}, client_Subscriber)
        servant_Revocations.mainService = main_Server
        
        return servant_Revocations
        
    def run(self, argv):
        
        """ Run the application, adding the needed objects to the adapter """

        logging.info("\n Running Client application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("Client")
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self)
        
        servant_Revocations = Revocations()
        topic_Manager = self.get_topic_manager()
        topic_Re="Revocations"
        try:
            topic_Revocations = topic_Manager.retrieve(topic_Re)
        
        except IceStorm.NoSuchTopic:
            print("\n No existe el topic")
            topic_Revocations = topic_Manager.create(topic_Re)
            
        topic_Revocations.subscribeAndGetPublisher({}, self.proxy)
        
        self.showMenu()
        self.manageMenu(False, False, False, None, servant_Revocations, self.adapter, topic_Manager)

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        return 0

    def showMenu(self, current=None):
        
        print(''' -------------------- Bienvenido a IceFlix CLI --------------------\n''')
        print('''Introduce "connect" para conectarte al servidor\n''')
        print('''Introduce "exit" para salir\n''')

    def manageMenu(self, exit, connect, login, main_Server, servant_Revocations, adapter, topic_Manager, current=None):
        
        while(exit is False):
            
            try:
                if connect is True and login is False:
                    print("\n IceFlix [Conectado] : ", end = '')
                    exit, connect, login, main_Server = self.manageConnect(exit, connect, login, main_Server, servant_Revocations)
                    
                elif connect is False and login is False:
                    print("\n IceFlix [Desconectado] : ", end = '')
                    exit, connect, login, main_Server = self.manageDisconnect(exit, connect, login, main_Server)
                
                elif connect is True and login is True:
                        print("\n IceFlix [Logueado] : ", end ='')
                        exit, connect, login, main_Server = self.manageLogin(exit, connect, login, main_Server, servant_Revocations)
                        
                else:
                    pass
                
            except EOFError:
                return 0

    def manageDisconnect(self, exit, connect, login, main_Server, current=None):

        inputS = input()
        option = inputS.split(" ", 1)
        
        if(option[0] == "connect"):
            
            try:
                proxy = self.communicator().stringToProxy(option[1])
                main_Server = IceFlix.MainPrx.checkedCast(proxy)
                
                if not main_Server:
                    raise RuntimeError('\n Proxy inválido')
                
                else:
                    connect = True
                    
            except Exception as error:
                logging.error(f'\n No se puede conectar {error}')
                
        elif (option[0] == "exit"):
            exit = True
            
        else:
            print("\n Opción incorrecta")
            
        return exit, connect, login, main_Server

    def manageConnect(self, exit, connect, login, main_Server, servant_Revocations, current=None):
        
        self.showOptionsConnect()
        option = input()
        option = option.split(" ")
        
        try:
            auth_proxy = main_Server.getAuthenticator()
            catalog_proxy = main_Server.getCatalog()
            
        except IceFlix.TemporaryUnavailable:
            logging.error('\n No hay ningún authenticator ni catálogo disponible')
        
        self.manageConnect(exit, connect, login, main_Server, servant_Revocations)
            
        if option[0] == "connect":
            print("\n Conectado")
            
        elif option[0] == "search":
            self.search_option(catalog_proxy)
            
        elif option[0] == "login":
            print("\n Introduce el usuario: ")
            user = input()
            password = getpass.getpass("\n Introduce la contraseña: ")
            final_password = hashlib.sha256(password.encode()).hexdigest()
            final_password = str(final_password)
            
            logging.debug('\n Intentando obtener la instancia 0 del Authenticator ')
            i = 0
            
            while i < 3:
                
                    if i > 0:
                        logging.debug('\nIntentando obtener la instancia "%s" del Authenticator', i)
                        
                    try:
                        auth_proxy = main_Server.getAuthenticator()
                        i=4
                        
                    except IceFlix.TemporaryUnavailable:
                        
                        if i < 2:
                            logging.warning('\n El Authenticator no está disponible temporalmente')
                            time.sleep(10.0)
                            
                        else:
                            logging.error('\n Fallo al obtener la instancia del Authenticator')
                    i=i+1
                    
            if i == 3:
                print("\nAuthentication service no disponible")
                
            else:
                try:
                    servant_Revocations.active =True
                    servant_Revocations.mainService = main_Server
                    servant_Revocations.client.user = user
                    servant_Revocations.client.password_hash = final_password
                    servant_Revocations.client.userToken = auth_proxy.refreshAuthorization(servant_Revocations.client.user, servant_Revocations.client.password_hash)
                    login = True
                    print("\n Autenticación realizada con éxito ")
                    
                except IceFlix.Unauthorized:
                    print("\n Fallo en la autenticación ")
        
        elif option[0] == "addUser":
            self.addUser_option(auth_proxy)
        
        elif option[0] == "removeUser":
            self.removeUser_option(auth_proxy)
        
        elif option[0] == "exit":
            exit = True

        return exit, connect, login, main_Server

    def manageLogin(self, exit, connect, login, main_Server, servant_Revocations, current=None):
        
        self.showOptionsLogin()
        option = input()
        option = option.split(" ")
        
        try:
            auth_proxy = main_Server.getAuthenticator()
            catalog_proxy = main_Server.getCatalog()
            
        except IceFlix.TemporaryUnavailable:
            logging.error('\n No hay ningún Authenticator ni Catalog disponible ')
            self.manageLogin(exit, connect, login, main_Server, servant_Revocations)
            
        if option[0] == "tag_search":
            print("\n Escribe las Tags a buscar: ")
            tags = input()
            tags = tags.split(" ")
            print("\n ¿Incluye todas las etiquetas? (Escribe True o False) ")
            includeAllTagsInput = input()
            
            try:
                if includeAllTagsInput == "True":
                    includeAllTags=True
                    
                elif includeAllTagsInput=="False":
                    includeAllTags=False
                
                media = catalog_proxy.getTilesByTags(tags, includeAllTags, servant_Revocations.client.userToken)
                
                for i in range(len(media)):
                    print (media[i])
                    
            except Exception as e:
                logging.error("\n Escribe True o False")
            
        elif option[0] == "logout":
            servant_Revocations.active=False
            login=False
            print("\n Se ha cerrado sesión con éxito\n")
            
        elif option[0] == "exit":
            exit=True
            
        elif option[0] == "search":
            self.search_option(catalog_proxy)
            
        elif option[0] == "addUser":
            self.addUser_option(auth_proxy)
            
        elif option[0] == "removeUser":
            self.removeUser_option(auth_proxy)
            
        elif option[0] == "addTags":
            print("\n Introduce el Identificador del Medio:")
            idMedia = input()
            print("\n Introduce las Tags: ")
            tagsend = []
            tags = input()
            tagsend = tags.split(" ")
            print(tagsend)
            
            try:
                catalog_proxy.addTags(idMedia,tagsend,servant_Revocations.client.userToken)
                
            except IceFlix.WrongMediaId:
                print("\n Identificador del Medio incorrecto")
                
        elif option[0] == "removeTags":
            print("\n Introduce el Identificador del Medio: ")
            idMedia = input()
            print("\n Introduce the Tags: ")
            tags = input()
            tags = tags.split(" ")
            print(tags)
            
            try:
                catalog_proxy.removeTags(idMedia, tags, servant_Revocations.client.userToken)
                
            except IceFlix.WrongMediaId:
                print("\n Identificador del Medio incorrecto")
                
                    
        elif option[0] == "renameTile":
            print("\n Introduce la contraseña del Administrador: ")
            adminToken = input()
            print("\n Introduce el Identificador del Medio: ")
            idMedia = input()
            print("\n Introduce el nuevo nombre para el Medio: ")
            newName = input()
            
            try:
                catalog_proxy.renameTile(idMedia, newName, adminToken)
                
            except IceFlix.WrongMediaId:
                print("\n Identificador del Medio incorrecto")

        return exit, connect, login, main_Server

    def removeUser_option(self, auth_proxy, current=None):
        
        print("\n Introduce la contraseña del Administrador: ")
        adminToken = input()
        print("\nIntroduce el nombre del usuario a eliminar: ")
        username = input()
        
        try:
            auth_proxy.removeUser(username, adminToken)
            
        except IceFlix.Unauthorized:
            print("\n Error del Administrador")
       


    def addUser_option(self, auth_proxy, current=None):
        
        print("\n Introduce la contraseña del Administrador: ")
        adminToken = input()
        print("\nIntroduce el nombre del nuevo usuario: ")
        username = input()
        password = getpass.getpass("\n Introduce la contraseña para el nuevo usuario: ")
        final_password = hashlib.sha256(password.encode()).hexdigest()
        final_password = str(final_password)
        
        try:
            auth_proxy.addUser(username, final_password, adminToken)
            
        except IceFlix.Unauthorized:
            print("\n Error del Administrador")

    def search_option(self, catalog_proxy, current=None):
        
        print("\n Introduce el nombre del Medio a buscar: ")
        
        name = input()
        print("\n ¿El nombre a buscar es exacto (Escribe True o False)? ")
        exactInput = input()
        
        try:
            if exactInput == "True":
                exact = True
            elif exactInput == "False":
                exact = False
                
        except Exception as e:
            logging.error("\n Escribe True o False")

        media = catalog_proxy.getTilesByName(name, exact)
        
        if len(media) == 0:
            print("\n No existen medios con este nombre")
        else:
            for i in range(len(media)):
                print (media[i])
        

    def showOptionsConnect(self,current=None):
        print('''\n\n-----------------------------
                    \n\nAcciones disponibles:
                    \n\nconnect
                    \nlogin
                    \nsearch
                    \naddUser
                    \nremoveUser
                    \nexit
                    \n\n-----------------------------''')

    def showOptionsLogin(self, current=None):
        print('''\n\n-----------------------------
                    \n\nAcciones disponibles:
                    \n\naddUser
                    \nremoveUser
                    \nsearch
                    \naddTags
                    \nremoveTags
                    \ntag_search
                    \nlogout
                    \nexit
                    \n\n-----------------------------''')
