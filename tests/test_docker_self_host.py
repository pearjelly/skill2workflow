import json
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts.docker_service_smoke import (
    CONTAINER_ROOT,
    _offline_args,
    _runtime_args,
    _verify_container_boundary,
)


ROOT = Path(__file__).resolve().parents[1]


class DockerSelfHostTests(TestCase):
    def test_restored_service_uses_only_the_selected_state_mount(self):
        original = Path("/tmp/workspace")
        restored = Path("/tmp/restore/state")
        args = _runtime_args(original, state_dir=restored)
        mounts = [args[index + 1] for index, item in enumerate(args[:-1]) if item == "--mount"]
        self.assertIn(
            f"type=bind,src={restored},dst={CONTAINER_ROOT}/state", mounts
        )
        self.assertNotIn(
            f"type=bind,src={original / 'state'},dst={CONTAINER_ROOT}/state", mounts
        )

    def test_offline_backup_mounts_exclude_credentials(self):
        args = _offline_args(Path("/tmp/workspace"), writable_backup=True, include_state=True)
        joined = " ".join(args)
        self.assertIn("--network none", joined)
        self.assertIn("/tmp/workspace/state", joined)
        self.assertIn("/tmp/workspace/backups", joined)
        self.assertNotIn("/tmp/workspace/secrets", joined)
        self.assertNotIn("/tmp/workspace/config", joined)
        verify_args = _offline_args(Path("/tmp/workspace"), writable_backup=False, include_state=False)
        self.assertIn("/backups,readonly", " ".join(verify_args))
        self.assertNotIn("/tmp/workspace/state", " ".join(verify_args))

    def test_smoke_rejects_a_writable_secret_mount(self):
        mounts = [
            {
                "Type": "bind",
                "Destination": f"{CONTAINER_ROOT}/{name}",
                "RW": name == "state",
                "Source": f"/tmp/workspace/{name}",
            }
            for name in ("config", "secrets", "backups", "state")
        ]
        details = [{
            "HostConfig": {"NetworkMode": "host", "ReadonlyRootfs": True},
            "Config": {"User": f"{os.getuid()}:{os.getgid()}"},
            "Mounts": mounts,
        }]
        with patch("scripts.docker_service_smoke._docker", side_effect=lambda *_: json.dumps(details)):
            _verify_container_boundary("service")
            _verify_container_boundary("service", expected_state_source=Path("/tmp/workspace/state"))
            mounts[1]["RW"] = True
            with self.assertRaisesRegex(RuntimeError, "mount write boundary"):
                _verify_container_boundary("service")
            mounts[1]["RW"] = False
            with self.assertRaisesRegex(RuntimeError, "restored state mount source"):
                _verify_container_boundary("service", expected_state_source=Path("/tmp/restore/state"))

    def test_image_is_non_root_and_installs_a_wheel(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn("pip wheel --no-deps", dockerfile)
        self.assertIn("--no-index --no-deps /wheelhouse/skill2workflow-*.whl", dockerfile)
        self.assertIn("USER 65532:65532", dockerfile)
        self.assertIn('ENTRYPOINT ["skill2workflow"]', dockerfile)
        self.assertIn("*\n!Dockerfile", ignore)
        self.assertIn("!examples/workflows/**", ignore)
        self.assertNotIn("COPY . .", dockerfile)

    def test_documented_runtime_preserves_existing_security_boundary(self):
        guide = (ROOT / "docs/docker-self-host.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("--network host", guide)
        self.assertIn("--host 127.0.0.1", guide)
        self.assertIn("--read-only", guide)
        self.assertIn("--cap-drop ALL", guide)
        self.assertIn("src=$HOST_ROOT/state,dst=/srv/skill2workflow/team-a/state", guide)
        self.assertIn("python3 scripts/docker_service_smoke.py", workflow)
        self.assertIn("skill2workflow:0.1.0 backup-verify", guide)
        self.assertIn("skill2workflow:0.1.0 restore", guide)
        self.assertIn("python3 scripts/docker_service_smoke.py",
                      (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8"))
        baseline = (ROOT / "docs/production-baseline-evidence.md").read_text(encoding="utf-8")
        self.assertIn("bundle does not build or run the optional Linux Docker image", baseline)
        self.assertIn("[Single-service Docker self-hosting](docker-self-host.md)",
                      (ROOT / "docs/README.md").read_text(encoding="utf-8"))
