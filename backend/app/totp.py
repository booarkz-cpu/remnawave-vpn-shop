import base64, hashlib, hmac, struct, time, secrets

def random_base32():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')

def code(secret: str, for_time: int|None=None, digits: int=6) -> str:
    counter=int((for_time if for_time is not None else time.time())//30)
    key=base64.b32decode(secret.upper()+('='*((8-len(secret)%8)%8)),casefold=True)
    msg=struct.pack('>Q',counter)
    digest=hmac.new(key,msg,hashlib.sha1).digest()
    offset=digest[-1]&0x0f
    number=(struct.unpack('>I',digest[offset:offset+4])[0]&0x7fffffff)%(10**digits)
    return str(number).zfill(digits)

def verify(secret: str, token: str, valid_window: int=1) -> bool:
    if not token.isdigit() or len(token)!=6: return False
    now=int(time.time())
    return any(hmac.compare_digest(code(secret,now+i*30),token) for i in range(-valid_window,valid_window+1))

def provisioning_uri(secret: str, name: str, issuer: str) -> str:
    from urllib.parse import quote
    return f"otpauth://totp/{quote(issuer)}:{quote(name)}?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
