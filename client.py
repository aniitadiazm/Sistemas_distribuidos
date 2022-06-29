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
        
        self.showMain()
        self.manageMenu(False, False, False, None, servant_Revocations, self.adapter, topic_Manager)

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        return 0

    def showMain(self, current=None):
        
        print(''' -------------------- Bienvenido a IceFlix CLI --------------------\n''')
        print('''Introduce "connect" para conectarte al servidor\n''')
        print('''Introduce "exit" para salir\n''')

    def manageMenu(self, exit, online, login, main_Server, servant_Revocations, adapter, topic_Manager, current=None):
        
        while(exit == False):
            
            try:
                if online == True and login == False:
                    print("\n IceFlix [Connect] : ", end= '')
                    exit, online, login, main_Server = self.manageConnect(exit, online, login, main_Server, servant_Revocations)
                    
                elif online == False and login == False:
                    print("\n IceFlix [Disconnect] : ", end = '')
                    exit, online,login,main_Server = self.manageDisconnect(exit, online, login, main_Server)
                
                elif login == True and online == True:
                        print("\n IceFlix [Logging] : ", end='')
                        exit, online,login,main_Server = self.manageLogin(exit, online, login, main_Server, servant_Revocations)
                        
                else:
                    pass
                
            except EOFError:
                return 0

    def manageDisconnect(self, exit, online, login, main_Server, current=None):

        inputS = input()
        option = inputS.split(" ", 1)
        
        if(option[0] == "connect"):
            
            try:
                proxy = self.communicator().stringToProxy(option[1])
                main_Server = IceFlix.MainPrx.checkedCast(proxy)
                
                if not main_Server:
                    raise RuntimeError('\n Proxy inválido')
                
                else:
                    online = True
                    
            except Exception as error:
                logging.error(f'\n No se puede conectar {error}')
                
        elif (option[0] == "exit"):
            exit = True
            
        else:
            print("\n Opción incorrecta")
            
        return exit, online, login, main_Server

    def manageConnect(self, exit, online, login, main_Server, servant_Revocations, current=None):
        
        self.showOptionsOnline()
        option = input()
        option = option.split(" ")
        
        try:
            auth_proxy = main_Server.getAuthenticator()
            catalog_proxy = main_Server.getCatalog()
            
        except IceFlix.TemporaryUnavailable:
            
            logging.error('\n No hay ningún authenticator ni catálogo disponible')
            self.manageConnect(exit, online, login, main_Server, servant_Revocations)
            
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
            
            logging.debug('\n Intentando obtener la instancia 0 del Authenticador')
            i = 0
            
            while i < 3:
                
                    if i > 0:
                        logging.debug('\nIntentando obtener la instancia "%s" del Authenticador', i)
                        
                    try:
                        auth_proxy = main_Server.getAuthenticator()
                        i=4
                        
                    except IceFlix.TemporaryUnavailable:
                        
                        if i < 2:
                            logging.warning('\nEl authenticator no está disponible temporalmente')
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
                    print("\n Autenticación realizada con éxito")
                    
                except IceFlix.Unauthorized:
                    print("\n Fallo en la autenticación")
        
        elif option[0] == "addUser":
            self.addUser_option(auth_proxy)
        
        elif option[0] == "removeUser":
            self.removeUser_option(auth_proxy)
        
        elif option[0] == "exit":
            exit = True

        return exit, online, login, main_Server

    def manageLogin(self, exit, online, login, main_Server, servant_Revocations, current=None):
        
        self.showOptionsLogin()
        option = input()
        option = option.split(" ")
        
        try:
            auth_proxy = main_Server.getAuthenticator()
            catalog_proxy = main_Server.getCatalog()
            
        except IceFlix.TemporaryUnavailable:
            logging.error('\nThere is no authenticator or catalog available')
            self.manageLogin(exit, online, login, main_Server, servant_Revocations)
            
        if option[0]=="tag_search":
            print("\nWrite the tags")
            tags = input()
            tags = tags.split(" ")
            print("\nincludeAllTags T/F ?")
            includeAllTagsInput = input()
            
            try:
                if includeAllTagsInput == "T":
                    includeAllTags=True
                    
                elif includeAllTagsInput=="F":
                    includeAllTags=False
                
                media = catalog_proxy.getTilesByTags(tags,includeAllTags,servant_Revocations.client.userToken)
                
                for i in range(len(media)):
                    print (media[i])
                    
            except Exception as e:
                logging.error("\n Bad input")
            
        elif option[0] == "logout":
            servant_Revocations.active=False
            login=False
            print("\n Succesfully logged out\n")
            
        elif option[0] == "exit":
            exit=True
            
        elif option[0] == "search":
            self.search_option(catalog_proxy)
            
        elif option[0] == "addUser":
            self.addUser_option(auth_proxy)
            
        elif option[0] == "removeUser":
            self.removeUser_option(auth_proxy)
            
        elif option[0] == "addTags":
            print("\nIntroduce the idMedia:")
            idTag=input()
            print("\nIntroduce the tags:")
            tagsend = []
            tags = input()
            tagsend = tags.split(" ")
            print(tagsend)
            
            try:
                catalog_proxy.addTags(idTag,tagsend,servant_Revocations.client.userToken)
                
            except IceFlix.WrongMediaId:
                print("\n Bad Id")
                
        elif option[0] == "removeTags":
            print("\n Introduce the idTag:")
            idTag=input()
            print("\n Introduce the tags:")
            tags = input()
            tags = tags.split(" ")
            print(tags)
            
            try:
                catalog_proxy.removeTags(idTag, tags, servant_Revocations.client.userToken)
                
            except IceFlix.WrongMediaId:
                print("\nError con el Id")
                
                    
        elif option[0] == "renameTile":
            print("\n Introduce the pass for admin:")
            adminToken=input()
            print("\n Introduce id:")
            id=input()
            print("\n Introduce the new name:")
            newName=input()
            
            try:
                catalog_proxy.renameTile(id, newName, adminToken)
                
            except IceFlix.WrongMediaId:
                print("Bad Id")

        return exit, online, login, main_Server

    def removeUser_option(self, auth_proxy, current=None):
        
        print("\nIntroduce la password del admin:")
        adminToken = input()
        
        print("\nIntroduce el nombre de usuario:")
        username = input()
        
        try:
            auth_proxy.removeUser(username, adminToken)
            
        except IceFlix.Unauthorized:
            print("Error del administrador")
       


    def addUser_option(self, auth_proxy, current=None):
        
        print("\n Introduce la password del admin:")
        adminToken = input()
        
        print("\n Introduce el nombre de usuario:")
        username = input()
        
        password = getpass.getpass("\n Introduce la contraseña: ")
        final_password = hashlib.sha256(password.encode()).hexdigest()
        final_password = str(final_password)
        
        try:
            auth_proxy.addUser(username, final_password, adminToken)
            
        except IceFlix.Unauthorized:
            print("Error del administrador")

    def search_option(self, catalog_proxy, current=None):
        
        print("\nIntroduce el nombre del medio:")
        
        name = input()
        print("\nEl nombre a buscar es exacto (Escribe True o False)?")
        exactInput = input()
        
        try:
            if exactInput == "True":
                exact=True
                
            elif exactInput == "False":
                exact=False
                
        except Exception as e:
            logging.error("\n Escribe True o False")
        media = catalog_proxy.getTilesByName(name, exact)
        
        if len(media)==0:
            print("\nNo existen medios con este nombre\n")
            
        else:
            for i in range(len(media)):
                print (media[i])
        

    def showOptionsOnline(self,current=None):
        print('''\n\n#####################################\nAvailable Options:\n\nconnect exit login\nsearch addUser removeUser\n\n#####################################''')

    def showOptionsLogin(self, current=None):
        print('''\n\n#####################################\nAvailable Options:\n\nexit logout addUser\nsearch tag_search removeUser\naddTags removeTags play\n\n#####################################''')
