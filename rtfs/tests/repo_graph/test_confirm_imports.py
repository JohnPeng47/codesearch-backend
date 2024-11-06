from rtfs.repo_resolution.repo_graph import RepoGraph
from conftest import repo_graph
import os

import pytest


@pytest.mark.parametrize(
    "repo_graph", ["tests/repos/test-confirm-imports"], indirect=["repo_graph"]
)
def test_confirm_imports(repo_graph: RepoGraph):
    imports = """browser.py -> utils.py
cli.py -> models.py
cli.py -> repo.py
repo.py -> core.py
repo.py -> models.py
cli.py -> browser.py
cli.py -> browser.py
cli.py -> exceptions.py
cli.py -> core.py
cli.py -> public.py
augment.py -> core.py
build_mapping.py -> core.py
experiment.py -> core.py
get_tms.py -> core.py
register.py -> core.py
remote_head.py -> core.py
core.py -> exceptions.py
base.py -> core.py
base.py -> exceptions.py
base.py -> utils.py
base.py -> utils.py
check_release.py -> core.py
models.py -> core.py
repo.py -> utils.py
repo.py -> exceptions.py
python.py -> models.py
python.py -> exceptions.py
python.py -> exceptions.py
client.py -> core.py
client.py -> models.py
find_race_cond.py -> python.py
find_race_cond.py -> core.py
find_race_cond.py -> models.py
"""

    assert imports == repo_graph.to_str()
