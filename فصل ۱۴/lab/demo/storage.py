import uuid
class DemoStorage:
    """Only a local contract simulator. The grant is not a real upload URL."""
    def __init__(self): self.objects={}
    def sign_upload(self,key,max_size):return {"key":key,"max_size":max_size,"expires_in":300}
    def put(self,key,data):self.objects[key]={"size":len(data),"generation":str(uuid.uuid4()),"data":data}
    def head(self,key):
        row=self.objects[key]
        return {"size":row["size"],"generation":row["generation"]}
