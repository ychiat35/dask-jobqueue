import sys

import dask
from dask.utils import format_bytes, parse_bytes

from dask_jobqueue import OARCluster


def test_header():
    with OARCluster(
        walltime="00:02:00",
        processes=4,
        cores=8,
        memory="28GB",
        oar_mem_core_property_name="memcore",
    ) as cluster:
        assert "#OAR -n dask-worker" in cluster.job_header
        assert "#OAR -l /nodes=1/core=8,walltime=00:02:00" in cluster.job_header
        assert "#OAR -p memcore>=3337" in cluster.job_header
        assert "#OAR --project" not in cluster.job_header
        assert "#OAR -q" not in cluster.job_header

    with OARCluster(
        queue="regular",
        project="DaskOnOar",
        processes=4,
        cores=8,
        memory="28GB",
        oar_mem_core_property_name="mem_core",
        job_extra_directives=["-t besteffort"],
    ) as cluster:
        assert "walltime=" in cluster.job_header
        assert "#OAR --project DaskOnOar" in cluster.job_header
        assert "#OAR -q regular" in cluster.job_header
        assert "#OAR -t besteffort" in cluster.job_header
        assert "#OAR -p mem_core>=3337" in cluster.job_header

    with OARCluster(
        cores=4, memory="8GB", oar_mem_core_property_name="memcore"
    ) as cluster:
        assert "#OAR -n dask-worker" in cluster.job_header
        assert "walltime=" in cluster.job_header
        assert "#OAR -p memcore" in cluster.job_header
        assert "#OAR --project" not in cluster.job_header
        assert "#OAR -q" not in cluster.job_header

    with OARCluster(
        walltime="00:02:00",
        processes=4,
        cores=8,
        memory="28GB",
        oar_mem_core_property_name="mem_core",
    ) as cluster:
        assert "#OAR -n dask-worker" in cluster.job_header
        assert "#OAR -l /nodes=1/core=8,walltime=00:02:00" in cluster.job_header
        assert "#OAR -p mem_core>=3337" in cluster.job_header

    with OARCluster(
        cores=8,
        memory="28GB",
        job_extra_directives=["-p cluster='yeti'"],
        oar_mem_core_property_name="memcore",
    ) as cluster:
        assert "#OAR -n dask-worker" in cluster.job_header
        assert "#OAR -l /nodes=1/core=8" in cluster.job_header
        assert "#OAR -p \"cluster='yeti' AND memcore>=3337\"" in cluster.job_header

    with OARCluster(
        cores=4,
        memory="28MB",
        job_extra_directives=["-p gpu_count=1"],
        oar_mem_core_property_name="mem_core",
    ) as cluster:
        assert "#OAR -n dask-worker" in cluster.job_header
        assert "walltime=" in cluster.job_header
        assert '#OAR -p "gpu_count=1 AND mem_core>=6"' in cluster.job_header


def test_job_script():
    with OARCluster(
        walltime="00:02:00",
        processes=4,
        cores=8,
        memory="28GB",
        oar_mem_core_property_name="memcore",
    ) as cluster:
        job_script = cluster.job_script()
        assert "#OAR" in job_script
        assert "#OAR -n dask-worker" in job_script
        formatted_bytes = format_bytes(parse_bytes("7GB")).replace(" ", "")
        assert f"--memory-limit {formatted_bytes}" in job_script
        assert "#OAR -l /nodes=1/core=8,walltime=00:02:00" in job_script
        assert "#OAR -p memcore>=3337" in job_script
        assert "#OAR --project" not in job_script
        assert "#OAR -q" not in job_script
        assert "export " not in job_script
        assert (
            "{} -m distributed.cli.dask_worker tcp://".format(sys.executable)
            in job_script
        )
        formatted_bytes = format_bytes(parse_bytes("7GB")).replace(" ", "")
        assert (
            f"--nthreads 2 --nworkers 4 --memory-limit {formatted_bytes}" in job_script
        )

    with OARCluster(
        walltime="00:02:00",
        processes=4,
        cores=8,
        memory="28GB",
        oar_mem_core_property_name="mem_core",
        job_script_prologue=[
            'export LANG="en_US.utf8"',
            'export LANGUAGE="en_US.utf8"',
            'export LC_ALL="en_US.utf8"',
        ],
    ) as cluster:
        job_script = cluster.job_script()
        assert "#OAR" in job_script
        assert "#OAR -n dask-worker" in job_script
        formatted_bytes = format_bytes(parse_bytes("7GB")).replace(" ", "")
        assert f"--memory-limit {formatted_bytes}" in job_script
        assert "#OAR -l /nodes=1/core=8,walltime=00:02:00" in job_script
        assert "#OAR -p mem_core>=3337" in job_script
        assert "#OAR --project" not in job_script
        assert "#OAR -q" not in job_script

        assert 'export LANG="en_US.utf8"' in job_script
        assert 'export LANGUAGE="en_US.utf8"' in job_script
        assert 'export LC_ALL="en_US.utf8"' in job_script

        assert (
            "{} -m distributed.cli.dask_worker tcp://".format(sys.executable)
            in job_script
        )
        formatted_bytes = format_bytes(parse_bytes("7GB")).replace(" ", "")
        assert (
            f"--nthreads 2 --nworkers 4 --memory-limit {formatted_bytes}" in job_script
        )


def test_config_name_oar_takes_custom_config():
    conf = {
        "queue": "myqueue",
        "project": "myproject",
        "ncpus": 1,
        "cores": 1,
        "memory": "2 GB",
        "walltime": "00:02",
        "job-extra": None,
        "job-extra-directives": [],
        "name": "myname",
        "processes": 1,
        "interface": None,
        "death-timeout": None,
        "local-directory": "/foo",
        "shared-temp-directory": None,
        "extra": None,
        "worker-extra-args": [],
        "env-extra": None,
        "job-script-prologue": [],
        "log-directory": None,
        "shebang": "#!/usr/bin/env bash",
        "job-cpu": None,
        "job-mem": None,
        "resource-spec": None,
        "oar-mem-core-property-name": "memcore",
    }

    with dask.config.set({"jobqueue.oar-config-name": conf}):
        with OARCluster(config_name="oar-config-name") as cluster:
            assert cluster.job_name == "myname"


def test_oar_mem_core_property_name_none_warning():
    import warnings

    # test issuing of warning
    warnings.simplefilter("always")

    job_cls = OARCluster.job_cls
    with warnings.catch_warnings(record=True) as w:
        # should give a warning
        job = job_cls(cores=1, memory="1 GB")
        assert len(w) == 1
        assert issubclass(w[0].category, UserWarning)
        assert (
            "The OAR property name corresponding to the memory per core of your cluster has not been set"
            in str(w[0].message)
        )
    with warnings.catch_warnings(record=True) as w:
        # should not give a warning
        job = job_cls(
            cores=1,
            memory="1 GB",
            oar_mem_core_property_name="memcore",
        )
        assert len(w) == 0
