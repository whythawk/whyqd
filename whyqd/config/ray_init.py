import ray
import os

from whyqd.config.settings import settings


def ray_start():
    # https://docs.ray.io/en/latest/ray-core/starting-ray.html
    # https://github.com/modin-project/modin/issues/3845
    # https://stackoverflow.com/questions/57765260/is-there-a-way-to-limit-ray-object-storage-max-memory-usage
    # 10**9 == 1gb ==> try 8gb?
    # https://docs.docker.com/compose/compose-file/compose-file-v3/#shm_size
    # dev_shm must be aligned in docker-compose, and note that it's not under `build`
    #   shm_size: "8gb"
    if not ray.is_initialized():
        ray.init(
            ignore_reinit_error=True,
            runtime_env={"env_vars": {"__MODIN_AUTOIMPORT_PANDAS__": "1"}},
            num_cpus=settings.WHYQD_CPUS,
            _memory=settings.WHYQD_MEMORY,
            object_store_memory=settings.WHYQD_MEMORY,
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


# from ..config.ray_init import ray_start
# ray_start()
