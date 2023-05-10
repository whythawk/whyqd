import ray
import os
import json
import shutil
from pathlib import Path

from whyqd.config.settings import settings


def clear_spillway() -> bool:
    # https://stackoverflow.com/a/56151260/295606
    # only do this if ray is not initialised, otherwise it'll crash. horribly.
    if not Path(settings.WHYQD_SPILLWAY).exists():
        return False
    for path in Path(settings.WHYQD_SPILLWAY).iterdir():
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
        except Exception as e:
            print(f"Failed to delete {path}. Reason: {e}")
    return True


def ray_start():
    # https://docs.ray.io/en/latest/ray-core/starting-ray.html
    # https://docs.ray.io/en/latest/ray-core/configure.html
    # https://github.com/modin-project/modin/issues/3845
    # https://stackoverflow.com/questions/57765260/is-there-a-way-to-limit-ray-object-storage-max-memory-usage
    # 10**9 == 1gb ==> try 8gb?
    # https://docs.ray.io/en/latest/ray-core/objects/object-spilling.html
    # Spilling is a way of paging from memory onto the drive.
    # https://docs.docker.com/compose/compose-file/compose-file-v3/#shm_size
    # In Docker, can choose to use dev_shm as a faster access than tmp
    # dev_shm must be aligned in docker-compose, and note that it's not under `build`
    #   shm_size: "8gb"
    if not ray.is_initialized():
        # clear the spill path of any old artifacts
        clear_spillway()
        # initialise
        ray.init(
            ignore_reinit_error=True,
            runtime_env={"env_vars": {"__MODIN_AUTOIMPORT_PANDAS__": "1"}},
            num_cpus=settings.WHYQD_CPUS,
            _memory=settings.WHYQD_MEMORY,
            object_store_memory=settings.WHYQD_MEMORY,
            _temp_dir=settings.WHYQD_SPILLWAY,
            _system_config={
                "object_spilling_config": json.dumps(
                    {
                        "type": "filesystem",
                        "params": {
                            "directory_path": settings.WHYQD_SPILLWAY,
                        },
                    },
                )
            },
        )
        os.environ["MODIN_ENGINE"] = "ray"
        os.environ["MODIN_OUT_OF_CORE"] = "true"
        os.environ["MODIN_MEMORY"] = str(settings.WHYQD_MEMORY)


def ray_stop():
    if ray.is_initialized():
        ray.shutdown()


def ray_restart():
    ray_stop()
    ray_start()


# from whyqd.config.ray_init import ray_start
# ray_start()
