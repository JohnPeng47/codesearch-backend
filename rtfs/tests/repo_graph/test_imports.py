from rtfs.repo_resolution.repo_graph import RepoGraph
from conftest import repo_graph
import os

import pytest

# TODO: BUG: repo_graph missing some
# go back to 27e6fd803e5cd60ac4d0ec6c631f605b2ef1ada3
# and compare the imports output being asserted against with repo_graph.to_str()


@pytest.mark.parametrize("repo_graph", ["tests/repos/cowboy"], indirect=["repo_graph"])
def test_imports_repo_graph(repo_graph: RepoGraph):
    imports = """browser.py::4 -> utils.py::2
browser.py::4 -> utils.py::4
cli.py::11 -> models.py::3
cli.py::11 -> models.py::1
cli.py::11 -> repo.py::2
cli.py::11 -> repo.py::9
cli.py::0 -> models.py::7
cli.py::0 -> build_mapping.py::1
cli.py::0 -> browser.py::4
cli.py::0 -> core.py::3
cli.py::0 -> base.py::5
repo.py::2 -> core.py::3
repo.py::2 -> models.py::3
cli.py::8 -> repo.py::9
cli.py::13 -> repo.py::9
cli.py::14 -> repo.py::5
cli.py::14 -> build_mapping.py::1
cli.py::14 -> augment.py::2
cli.py::14 -> remote_head.py::1
repo.py::5 -> exceptions.py::1
cli.py::5 -> register.py::1
cli.py::5 -> public.py::1
cli.py::16 -> get_tms.py::1
cli.py::20 -> manager.py::1
cli.py::20 -> exceptions.py::1
cli.py::20 -> check_release.py::1
base.py::5 -> utils.py::2
check_release.py::1 -> core.py::3
augment.py::0 -> base.py::5
augment.py::0 -> core.py::3
build_mapping.py::0 -> base.py::5
build_mapping.py::0 -> core.py::3
experiment.py::0 -> base.py::5
experiment.py::0 -> core.py::3
get_tms.py::0 -> base.py::5
get_tms.py::0 -> core.py::3
register.py::0 -> base.py::5
register.py::0 -> core.py::3
remote_head.py::0 -> base.py::5
remote_head.py::0 -> core.py::3
core.py::1 -> exceptions.py::1
core.py::5 -> check_release.py::2
base.py::6 -> core.py::3
base.py::14 -> exceptions.py::1
models.py::8 -> core.py::3
repo.py::8 -> utils.py::1
python.py::16 -> models.py::3
python.py::16 -> exceptions.py::1
python.py::15 -> exceptions.py::1
client.py::3 -> python.py::15
client.py::4 -> python.py::15
client.py::4 -> models.py::3
client.py::0 -> core.py::3
client.py::0 -> base.py::5
client.py::2 -> base.py::5
find_race_cond.py::0 -> python.py::15
find_race_cond.py::0 -> base.py::5
find_race_cond.py::0 -> core.py::3
find_race_cond.py::0 -> models.py::3
"""

    print(repo_graph.to_str())
    assert imports == repo_graph.to_str()
