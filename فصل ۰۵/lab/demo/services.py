from django.core.cache import caches
from .algorithms import HashRing
class ShardedCache:
    def __init__(self, nodes):
        self.ring=HashRing(nodes)
    def get(self,key,default=None):
        return caches[self.ring.owner(key)].get(key,default)
    def set(self,key,value,timeout=30):
        return caches[self.ring.owner(key)].set(key,value,timeout)
