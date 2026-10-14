import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from demo.services import ShardedCache
from demo.algorithms import HashRing
client=ShardedCache(["cache-a","cache-b","cache-c"])
client.set("book:1",{"price":"150"})
print("owner:",client.ring.owner("book:1"),"value:",client.get("book:1"))
new=HashRing(["cache-a","cache-b","cache-c","cache-d"])
print("moved out of 1000:",sum(client.ring.owner(str(i))!=new.owner(str(i)) for i in range(1000)))
