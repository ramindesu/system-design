from .services import normalize
class TopKTrie:
    def __init__(self,rows,k=5):
        if type(k) is not int or k<1:raise ValueError("positive k required")
        self.root={"children":{},"top":[]}
        seen=set()
        for term,score in sorted(rows,key=lambda row:(-row[1],normalize(row[0]))):
            text=normalize(term)
            if text in seen:continue
            seen.add(text);node=self.root
            for char in text:
                node=node["children"].setdefault(char,{"children":{},"top":[]})
                if len(node["top"])<k:node["top"].append(term)
    def suggest(self,prefix):
        text=normalize(prefix)
        if not 2<=len(text)<=40:return []
        node=self.root
        for char in text:
            node=node["children"].get(char)
            if node is None:return []
        return list(node["top"])
