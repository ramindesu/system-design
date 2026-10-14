import os
class S3Storage:
    """Optional connector. Requires a versioned private bucket and boto3 credentials."""
    def __init__(self):
        import boto3
        self.client=boto3.client("s3");self.bucket=os.environ["VIDEO_BUCKET"]
    def sign_upload(self,key,max_size):
        return self.client.generate_presigned_post(Bucket=self.bucket,Key=key,
            Fields={"Content-Type":"video/mp4"},
            Conditions=[{"Content-Type":"video/mp4"},["content-length-range",1,max_size]],ExpiresIn=300)
    def head(self,key):
        value=self.client.head_object(Bucket=self.bucket,Key=key)
        version=value.get("VersionId")
        if not version or version=="null":raise ValueError("versioned bucket is required for this connector")
        return {"size":value["ContentLength"],"generation":version}
