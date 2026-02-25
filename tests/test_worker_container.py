import os
import yaml

def test_dockerfile_exists():
    assert os.path.exists("Dockerfile.worker")
    with open("Dockerfile.worker", "r") as f:
        content = f.read()
        assert "python:3.12" in content
        assert "core.runtime.worker.daemon" in content

def test_docker_compose_exists():
    assert os.path.exists("docker-compose.yml")
    with open("docker-compose.yml", "r") as f:
        config = yaml.safe_load(f)
        assert "services" in config
        assert "redis" in config["services"]
        assert "worker" in config["services"]
        assert config["services"]["worker"]["build"]["dockerfile"] == "Dockerfile.worker"

def test_worker_runnable_locally():
    """Ensure we haven't broken local runnability while containerizing."""
    # This just checks that the module can be imported without error
    import core.runtime.worker.daemon as daemon
    assert daemon.DistributedWorker is not None
