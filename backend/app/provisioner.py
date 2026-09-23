import io, os, shlex, time, base64, hashlib, logging
import paramiko

logger = logging.getLogger("remnawave.provisioner")

class ProvisionError(RuntimeError):
    pass

class _FingerprintPolicy(paramiko.MissingHostKeyPolicy):
    def __init__(self, expected): self.expected=expected
    def missing_host_key(self, client, hostname, key):
        actual="SHA256:"+base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
        if not self.expected or not hmac_compare(actual, self.expected):
            raise ProvisionError("SSH host key is not trusted; provide ssh_host_key fingerprint")
        client.get_host_keys().add(hostname, key.get_name(), key)

def hmac_compare(a,b):
    import hmac
    return hmac.compare_digest(a,b)

def _connect(host, port, username, password=None, private_key=None, timeout=20, host_key_fingerprint=None):
    client=paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(_FingerprintPolicy(host_key_fingerprint))
    kwargs=dict(hostname=host,port=int(port),username=username,timeout=timeout,
                banner_timeout=timeout,auth_timeout=timeout)
    if private_key:
        key=paramiko.Ed25519Key.from_private_key(io.StringIO(private_key))
        kwargs["pkey"]=key
    elif password:
        kwargs["password"]=password
    else:
        raise ProvisionError("SSH password or private_key is required")
    client.connect(**kwargs)
    return client

def run_ssh(host,port,username,password,private_key,compose_yaml,panel_ip,node_port=2222,host_key_fingerprint=None):
    if not compose_yaml.strip(): raise ProvisionError("compose_yaml is empty")
    if len(compose_yaml)>200_000: raise ProvisionError("compose_yaml too large")
    # Basic guardrails: we only write the node compose file and install Docker.
    if "remnawave/node" not in compose_yaml:
        raise ProvisionError("Compose must contain remnawave/node image")
    if not (1<=int(node_port)<=65535): raise ProvisionError("Invalid node port")
    client=_connect(host,port,username,password,private_key,host_key_fingerprint=host_key_fingerprint)
    try:
        cmds=[
            "set -e",
            "command -v docker >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh",
            "docker compose version >/dev/null 2>&1 || true",
            "mkdir -p /opt/remnanode",
            f"printf '%s' {shlex.quote(compose_yaml)} > /opt/remnanode/docker-compose.yml",
            "cd /opt/remnanode && docker compose pull",
            "cd /opt/remnanode && docker compose up -d",
            "cd /opt/remnanode && docker compose ps",
        ]
        # If ufw exists, restrict NODE_PORT to the panel IP as recommended by RW docs.
        if panel_ip:
            cmds.append(
                f"(command -v ufw >/dev/null 2>&1 && "
                f"ufw allow from {shlex.quote(panel_ip)} to any port {int(node_port)} proto tcp) || true"
            )
        command=" && ".join(cmds)
        stdin,stdout,stderr=client.exec_command(command,timeout=180)
        out=stdout.read().decode(errors="replace")
        err=stderr.read().decode(errors="replace")
        rc=stdout.channel.recv_exit_status()
        if rc!=0:
            logger.warning("Remote install failed (%s): %s", rc, err[-4000:])
            raise ProvisionError("Remote install failed")
        return {"ok":True,"host":host,"directory":"/opt/remnanode"}
    finally:
        client.close()
