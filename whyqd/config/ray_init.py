import ray
import os
# import json
import shutil
from pathlib import Path

from whyqd.config.settings import settings


def clear_spillway() -> bool:
    # https://stackoverflow.com/a/56151260/295606
    # only do this if ray is not initialised, otherwise it'll crash. horribly.
    WHYQD_SPILLWAY = ray._common.utils.get_user_temp_dir()
    if not Path(WHYQD_SPILLWAY).exists():
        return False
    for path in Path(WHYQD_SPILLWAY).iterdir():
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
        except Exception as e:
            print(f"Failed to delete {path}. Reason: {e}")
    return True


def ray_start(**kwargs):
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
        # initialise - kwargs allow overwriting of the settings (or ignoring the .env)
        kwargs["ignore_reinit_error"] = True
        kwargs["runtime_env"] = {"env_vars": {"__MODIN_AUTOIMPORT_PANDAS__": "1"}}
        if not kwargs.get("num_cpus") and settings.WHYQD_CPUS:
            kwargs["num_cpus"] = settings.WHYQD_CPUS
        if not kwargs.get("_memory") and settings.WHYQD_MEMORY:
            kwargs["_memory"] = settings.WHYQD_MEMORY
        if not kwargs.get("object_store_memory") and settings.WHYQD_MEMORY:
            kwargs["object_store_memory"] = settings.WHYQD_MEMORY
        if not kwargs.get("_temp_dir") and settings.WHYQD_SPILLWAY:
            # TODO: On some environments, I'm getting weird timeouts
            if not ray._common.utils.get_user_temp_dir().endswith(settings.WHYQD_SPILLWAY):
                kwargs["_temp_dir"] = f"{ray._common.utils.get_user_temp_dir()}{settings.WHYQD_SPILLWAY}"
            pass
        # if not kwargs.get("_system_config") and settings.WHYQD_SPILLWAY:
        #     kwargs["_system_config"] = {
        #         "object_spilling_config": json.dumps(
        #             {
        #                 "type": "filesystem",
        #                 "params": {
        #                     "directory_path": str(settings.WHYQD_SPILLWAY),
        #                 },
        #             },
        #         )
        #     }
        ray.init(**kwargs)
        os.environ["MODIN_ENGINE"] = "ray"
        os.environ["MODIN_OUT_OF_CORE"] = "true"
        if kwargs.get("_memory"):
            os.environ["MODIN_MEMORY"] = str(kwargs["_memory"])
        if kwargs.get("_temp_dir"):
            os.environ["RAY_TMPDIR"] = kwargs["_temp_dir"]


def ray_stop():
    if ray.is_initialized():
        ray.shutdown()


def ray_restart():
    ray_stop()
    ray_start()
