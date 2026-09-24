# Single-Service Docker Self-Hosting

This is one **Linux Docker Engine** deployment of one self-hosted,
single-tenant `skill2workflow` service. Docker host networking lets the
existing service keep its enforced `127.0.0.1` listener on the host. No port
is published. Docker Desktop, remote Docker daemons, Kubernetes, public
listeners, and multiple active service replicas are outside this path.

The image contains only the installed wheel and public packaged assets. The
build context uses an allowlist; configuration, SQLite state, and secrets are
never baked into the image. A short-lived initialization container creates
the workspace; the only long-running container is the service.

## Build and initialize

Run these Bash or Zsh commands as a **dedicated non-root Linux account** with
access to the local Docker Engine. Docker daemon access is host-privileged;
protect that account accordingly. Work from the repository root:

```bash
umask 077
docker build --tag skill2workflow:0.1.0 .
install -d -m 0700 "$HOME/skill2workflow"
HOST_PARENT="$(realpath "$HOME/skill2workflow")"
HOST_ROOT="$HOST_PARENT/team-a"
S2W_USER="$(id -u):$(id -g)"

docker run --rm --network none --user "$S2W_USER" \
  --mount "type=bind,src=$HOST_PARENT,dst=/srv/skill2workflow" \
  skill2workflow:0.1.0 service-init \
  --root /srv/skill2workflow/team-a --host 127.0.0.1 --port 8080
```

`HOST_ROOT` must not already exist. Initialization generates a private ingress
token and config with container-absolute paths; it does not print the token.
For the built-in HTTP connector, add reviewed `--http-allowed-origin` values
to `service-init`. For the approved Feishu China credential, add the
non-secret `--lark-app-id` and `--lark-app-secret-handle` options, then place
the App Secret in the generated private connector directory using your secret
manager. Never pass a credential value as a CLI argument or Docker environment
variable.

Check the workspace before starting the service:

```bash
S2W_MOUNTS=(
  --mount "type=bind,src=$HOST_ROOT/config,dst=/srv/skill2workflow/team-a/config,readonly"
  --mount "type=bind,src=$HOST_ROOT/secrets,dst=/srv/skill2workflow/team-a/secrets,readonly"
  --mount "type=bind,src=$HOST_ROOT/backups,dst=/srv/skill2workflow/team-a/backups,readonly"
  --mount "type=bind,src=$HOST_ROOT/state,dst=/srv/skill2workflow/team-a/state"
)

docker run --rm --network host --user "$S2W_USER" --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  "${S2W_MOUNTS[@]}" skill2workflow:0.1.0 service-doctor \
  --config /srv/skill2workflow/team-a/config/service.json
```

Doctor must report `ready`. Keep the generated `config/` and `secrets/`
directories owner-only. Do not use a broad shared mount, a Docker socket mount,
or a second service instance against the same SQLite state.

## Start and verify

```bash
docker run --detach --name skill2workflow --restart unless-stopped \
  --network host --user "$S2W_USER" --read-only \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 128 \
  --stop-timeout 60 \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
  "${S2W_MOUNTS[@]}" skill2workflow:0.1.0

curl --fail http://127.0.0.1:8080/readyz
docker exec skill2workflow skill2workflow service-go-live-check \
  --config /srv/skill2workflow/team-a/config/service.json \
  --service-url http://127.0.0.1:8080 \
  --auth-token-file /srv/skill2workflow/team-a/secrets/ingress-token
```

The go-live check remains provider-free by default. Add
`--verify-lark-tenant-credential` only for an explicitly approved Feishu
credential preflight. This does not create a Feishu task.

Docker logs contain application diagnostics, not a secret-delivery channel.
Use the existing authenticated service API or the installed UI from the same
host. Cross-host access still requires an independently configured TLS reverse
proxy and firewall boundary. Do not replace `--network host` with `-p` and
change the service bind address to `0.0.0.0`.

## Persistence, updates, and recovery

`state/` is the sole writable runtime mount. `config/`, `secrets/`, and
`backups/` are read-only in the running container. The state is retained when
the container stops or is replaced. Stop the service before an offline state
backup, restore, or migration; use the documented [backup and restore](backup-restore.md)
and [state upgrade](upgrade-migration.md) procedures in a separate one-off
container with only the necessary explicit write mounts. Credential files
need an independent secure backup and rotation path; state backups do not
include them.

For one offline backup, stop the service and wait for `docker stop` to return.
The one-off command mounts SQLite state writable because the backup code must
take database locks; it mounts the backup parent writable to publish one new,
non-overwriting set. It mounts neither configuration nor credentials:

```bash
docker stop --time 60 skill2workflow
BACKUP_NAME="backup-$(date -u +%Y%m%dT%H%M%SZ)"
docker run --rm --network none --user "$S2W_USER" --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
  --mount "type=bind,src=$HOST_ROOT/state,dst=/srv/skill2workflow/team-a/state" \
  --mount "type=bind,src=$HOST_ROOT/backups,dst=/srv/skill2workflow/team-a/backups" \
  skill2workflow:0.1.0 backup \
  --state-dir /srv/skill2workflow/team-a/state \
  --output-dir "/srv/skill2workflow/team-a/backups/$BACKUP_NAME"

docker run --rm --network none --user "$S2W_USER" --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
  --mount "type=bind,src=$HOST_ROOT/backups,dst=/srv/skill2workflow/team-a/backups,readonly" \
  skill2workflow:0.1.0 backup-verify \
  --backup-dir "/srv/skill2workflow/team-a/backups/$BACKUP_NAME"
```

Require `status: "valid"` before copying the set to separately controlled,
encrypted storage. If backup or verification fails, do not resume traffic
until the state and failure have been reviewed. After a successful backup,
`docker start skill2workflow` restarts the original service; require `/readyz`
and the authenticated go-live check again.

For a recovery drill, restore into a **new** owner-only sibling directory. The
destination `state` child must not exist, and this does not switch the running
service to restored state:

```bash
install -d -m 0700 "$HOST_PARENT/restore-candidate"
docker run --rm --network none --user "$S2W_USER" --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
  --mount "type=bind,src=$HOST_ROOT/backups,dst=/srv/skill2workflow/team-a/backups,readonly" \
  --mount "type=bind,src=$HOST_PARENT/restore-candidate,dst=/restore" \
  skill2workflow:0.1.0 restore \
  --backup-dir "/srv/skill2workflow/team-a/backups/$BACKUP_NAME" \
  --state-dir /restore/state
```

Review the restored state, then follow the [restore cutover contract](backup-restore.md)
before starting exactly one service against it. Never overwrite the current
`state/` directory with a restore or start two containers on the same state.

To update, first qualify the new image and workspace with a one-off Doctor,
then stop and remove the old service container and start **one** new service
container from the reviewed image. Keep the old image and a verified offline
backup until readiness, authenticated go-live checks, and recovery checks pass.
Never start old and new images concurrently on the same workspace. The
application does not promise exactly-once external effects, automatic
reconciliation, or rollback of provider requests.

The Linux container smoke gate builds this Dockerfile, initializes a fresh
workspace, passes Doctor and go-live checks, verifies actual container mounts
and user identity, proves offline backup/verification/fresh restore, restarts
the service, and confirms state persistence:

```bash
python3 scripts/docker_service_smoke.py
```
