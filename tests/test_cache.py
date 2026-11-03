"""The layered cache: this container's disk, the shared bucket, and the seed shipped with the app."""

import io
import json

from weatherwise.cache import FileCache, LayeredCache, S3Cache
from weatherwise.mcp_server.services import SEED_ROOT


class FakeS3:
    def __init__(self, fail: bool = False):
        self.objects: dict[str, bytes] = {}
        self.fail = fail

    def get_object(self, Bucket, Key):
        if self.fail or Key not in self.objects:
            raise RuntimeError("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, Bucket, Key, Body, ContentType):
        if self.fail:
            raise RuntimeError("unreachable")
        self.objects[Key] = Body


def test_a_value_saved_by_one_container_is_read_by_another(tmp_path):
    s3 = FakeS3()
    website = LayeredCache([FileCache(tmp_path / "web"), S3Cache("b", client=s3)])
    agents = LayeredCache([FileCache(tmp_path / "agents"), S3Cache("b", client=s3)])
    website.put("normals", "cell:18.50:76.50", {"t95": 33.1})
    assert agents.get("normals", "cell:18.50:76.50") == {"t95": 33.1}
    assert FileCache(tmp_path / "agents").get("normals", "cell:18.50:76.50") == {"t95": 33.1}  # copied nearer


def test_a_copied_entry_keeps_its_age(tmp_path):
    clock = [0.0]
    s3 = FakeS3()
    LayeredCache([S3Cache("b", client=s3)], now=lambda: clock[0]).put("forecast", "k", 1)
    clock[0] = 2 * 3600  # 2 of the forecast's 3 hours gone when the agents first read it
    local = FileCache(tmp_path, now=lambda: clock[0])
    cache = LayeredCache([local, S3Cache("b", client=s3)], now=lambda: clock[0])
    assert cache.get("forecast", "k") == 1
    clock[0] = 4 * 3600
    assert cache.get("forecast", "k") is None  # expired on the original schedule, not 3 h after the copy


def test_an_unreachable_bucket_is_a_miss_not_an_error(tmp_path):
    cache = LayeredCache([FileCache(tmp_path), S3Cache("b", client=FakeS3(fail=True))])
    assert cache.get("normals", "k") is None
    cache.put("normals", "k", 5)
    assert cache.get("normals", "k") == 5


def test_the_seed_is_read_but_never_written(tmp_path):
    seed = tmp_path / "seed"
    FileCache(seed).put("normals", "k", 7)
    cache = LayeredCache([FileCache(tmp_path / "disk"), FileCache(seed, read_only=True)])
    assert cache.get("normals", "k") == 7
    cache.put("normals", "k2", 8)
    assert FileCache(seed).get("normals", "k2") is None


def test_the_shipped_seed_is_long_lived_data_only():
    kinds = {p.name for p in SEED_ROOT.iterdir() if p.is_dir()}
    assert kinds <= {"normals", "flood_level", "admin", "elevation"}
    for path in SEED_ROOT.glob("*/*.json"):
        entry = json.loads(path.read_text())
        assert set(entry) == {"key", "saved_at", "value"}
        assert entry["saved_at"] > 0
