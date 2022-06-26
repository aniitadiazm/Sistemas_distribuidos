#!/usr/bin/python3
# -*- coding: utf-8 -*-hashlib

import sys
import Ice
Ice.loadSlice('IceFlix.ice')
import IceFlix

from Authenticator import Revocations
import threading
import getpass
import IceStorm
import hashlib
import time
import logging
import random


USER = ""
CURRENT_TOKEN = 'current_token'
PASSWORD_HASH = 'password_hash'
DEFAULT_TOPICMANAGER_PROXY = 'IceStorm/TopicManager:tcp -p 10000'


class Client():
    
    def __init__(self, token, password_hash, user):
        self.token = token
        self.password_hash = password_hash
        self.user = user

class Client(Ice.Application):

    def get_topic_manager(self):
        proxy=self.communicator().stringToProxy(DEFAULT_TOPICMANAGER_PROXY)
        if proxy is None:
            print("property {} not set".format(DEFAULT_TOPICMANAGER_PROXY))
            return None

        print("Using IceStorm in: '%s'" % DEFAULT_TOPICMANAGER_PROXY)
        return IceStorm.TopicManagerPrx.checkedCast(proxy)

    def connectRevocations(self,adapter,topicManager,main_Server):
        servant_Revocations=Revocations()
        client_Subscriber=adapter.addWithUUID(servant_Revocations)

        topicRe="Revocations"
        try:
            topic_Revocations=topicManager.retrieve(topicRe)
        except IceStorm.NoSuchTopic:
            print("No such topic")
            topic_Revocations=topicManager.create(topicRe)
        
        topic_Revocations.subscribeAndGetPublisher({},client_Subscriber)
        servant_Revocations.mainService=main_Server
        return servant_Revocations
    
    def subscriberClient(self,adapter,topicManager,sincTopic,main_Server):
        servant_StreamSync=StreamSync()
        client_Subscriber=adapter.addWithUUID(servant_StreamSync)

        topicRe=sincTopic
        try:
            topic_Revocations=topicManager.retrieve(topicRe)
        except IceStorm.NoSuchTopic:
            print("No such topic")
            topic_Revocations=topicManager.create(topicRe)
        
        topic_Revocations.subscribeAndGetPublisher({},client_Subscriber)
        servant_StreamSync.mainService=main_Server
        return servant_StreamSync
        
    def run(self, argv):

        broker = self.communicator()
        topicManager=self.get_topic_manager()
        adapter = broker.createObjectAdapterWithEndpoints("IceFlixAdapter","tcp")
        servant_Revocations=Revocations()
        client_Subscriber=adapter.addWithUUID(servant_Revocations)

        topicRe="Revocations"
        try:
            topic_Revocations=topicManager.retrieve(topicRe)
        except IceStorm.NoSuchTopic:
            print("No such topic")
            topic_Revocations=topicManager.create(topicRe)
        
        topic_Revocations.subscribeAndGetPublisher({},client_Subscriber)
        
        adapter.activate()

        self.showMain()
        self.manageMenu(False,False,False,None, servant_Revocations, adapter, topicManager)

        self.shutdownOnInterrupt()