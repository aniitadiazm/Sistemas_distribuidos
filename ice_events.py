import logging

import IceStorm

from common import ICESTORM_PROXY_PROPERTY
# pylint: disable=W1202
# pylint: disable=E1101
# pylint: disable=W0231

class IceEventsError(Exception):
    
    """  Excepción lanzada en caso de error en los eventos de ice """
    
    def __init__(self, msg='unknown error'):
        
        self._msg_ = msg

    def __str__(self):
        
        return 'IceStorm error: {}'.format(self._msg_)


class IceEvents:
    
    """ Manejar los objetos Suscriptores/Publicadores """
    
    def __init__(self, broker, property_name = ICESTORM_PROXY_PROPERTY):
        
        self._communicator_ = broker
        self._property_name_ = property_name
        self._topic_manager_ = None

    @property
    def topic_manager(self):
        
        """ Referencia a IceStorm::TopicManager """
        
        if not self._topic_manager_:
            proxy = self._communicator_.propertyToProxy(self._property_name_)
            
            if proxy is None:
                logging.error('La propiedad "{}" resulta ser un proxy nulo'.format(self._property_name_))
                raise IceEventsError('Falta la propiedad: {}'.format(self._property_name_))
            
            self._topic_manager_ = IceStorm.TopicManagerPrx.checkedCast(proxy)
            
        return self._topic_manager_

    def communicator(self):
        
        """ Get Ice::Communicator() """
        
        return self._communicator_

    def get_topic(self, name):
        
        """ Get IceStorm::Topic object"""
        
        try:
            topic = self.topic_manager.retrieve(name)
            
        except IceStorm.NoSuchTopic:
            logging.warning('IceStorm::Topic({}) not found!'.format(name))
            topic = self.topic_manager.create(name)
            
        return topic

    def get_publisher(self, topic_name):
        
        """Get IceStorm::Publisher object """
        
        topic = self.get_topic(topic_name)
        return topic.getPublisher()

    def subscribe(self, topic_name, proxy):
        
        """ Suscribirse a un objeto dado IceStorm::Topic object """
        
        topic = self.get_topic(topic_name)
        topic.subscribeAndGetPublisher({}, proxy)

    def unsubscribe(self, topic_name, proxy):
        
        """ Darse de baja de un objeto dado IceStorm::Topic object """
        
        topic = self.get_topic(topic_name)
        topic.unsubscribe(proxy)


