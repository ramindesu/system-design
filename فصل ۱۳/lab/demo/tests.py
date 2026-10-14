from django.test import TestCase
from django.core.cache import cache
from .models import Suggestion
from .services import normalize,suggest
from .trie import TopKTrie
class AutocompleteTests(TestCase):
    def setUp(self):
        cache.clear()
        for term,score in [("کتاب جنگو",100),("کتاب پایتون",80)]:
            Suggestion.objects.create(term=term,normalized=normalize(term),score=score)
    def test_persian_normalization_and_ranking(self):
        self.assertEqual(suggest("كت"),["کتاب جنگو","کتاب پایتون"])
        self.assertEqual(normalize("علي"),"علی")
    def test_empty_result_is_cached(self):
        with self.assertNumQueries(1):self.assertEqual(suggest("zz"),[])
        with self.assertNumQueries(0):self.assertEqual(suggest("zz"),[])
        with self.assertNumQueries(0):self.assertEqual(suggest("ک"),[])
    def test_trie_top_k_and_unknown_prefix(self):
        trie=TopKTrie([("کتاب پایتون",80),("کتاب جنگو",100)],k=1)
        self.assertEqual(trie.suggest("كت"),["کتاب جنگو"])
        self.assertEqual(trie.suggest("zz"),[])
