import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.core.cache import cache
from demo.models import Suggestion
from demo.services import normalize,suggest
from demo.trie import TopKTrie
rows=[("کتاب جنگو",100),("کتاب پایتون",80)]
for term,score in rows:
 Suggestion.objects.update_or_create(normalized=normalize(term),defaults={"term":term,"score":score})
cache.clear()
print("SQL suggestions:",suggest("كت"))
print("Trie suggestions:",TopKTrie(rows,k=1).suggest("كت"))
