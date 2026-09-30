from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl,urlencode,urlsplit,urlunsplit
from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
    app_name:str; app_env:str; debug:bool
    mongodb_url:str|None=None; mongodb_write_url:str|None=None; mongodb_read_url:str|None=None; mongodb_database:str
    mongodb_read_preference:Literal["secondary","secondaryPreferred"]="secondaryPreferred"; mongodb_write_timeout_ms:int=5000
    kafka_bootstrap_servers:str; kafka_topic:str; kafka_test_partitions:int; kafka_consumer_group:str; kafka_auto_offset_reset:str
    kafka_chat_consumer_group:str="study-group-chat-fanout"; kafka_chat_partitions:int=3; chat_media_max_size_mb:int=50
    model_config=SettingsConfigDict(env_file=".env",env_file_encoding="utf-8",case_sensitive=False,extra="ignore")
    @property
    def database_write_url(self)->str:
        u=self.mongodb_write_url or self.mongodb_url
        if u is None: raise ValueError("MONGODB_WRITE_URL (or legacy MONGODB_URL) is required")
        return _with_uri_options(u,{"readPreference":"primary","w":"majority","wtimeoutMS":self.mongodb_write_timeout_ms})
    @property
    def database_read_url(self)->str:
        u=self.mongodb_read_url or self.mongodb_write_url or self.mongodb_url
        if u is None: raise ValueError("MONGODB_READ_URL or a write URL must be configured")
        return _with_uri_options(u,{"readPreference":self.mongodb_read_preference,"readConcernLevel":"majority"})
def _with_uri_options(uri:str,options:dict[str,str|int])->str:
    p=urlsplit(uri); names={k.lower() for k in options}; q=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if k.lower() not in names]; q.extend((k,str(v)) for k,v in options.items()); return urlunsplit((p.scheme,p.netloc,p.path or "/",urlencode(q),p.fragment))
@lru_cache
def get_settings()->Settings:return Settings()
settings=get_settings()
