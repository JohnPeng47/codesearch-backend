from pathlib import Path
import json
import importlib.resources as pkg_resources
import asyncio
from networkx import MultiDiGraph
import click

import cProfile
import pstats
import io
from pstats import SortKey
from pathlib import Path
from functools import wraps
import asyncio
import traceback

from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.summarize.summarize import Summarizer
from rtfs.file_resolution.file_graph import FileGraph
from rtfs.chunker import chunk

GRAPH_FOLDER = pkg_resources.files("rtfs") / "graphs"


def sync_profile_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()

        result = func(*args, **kwargs)

        pr.disable()

        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats(SortKey.CUMULATIVE)
        ps.dump_stats("profile.txt")

        print(f"Profiling results for {func.__name__}:")
        print(s.getvalue())

        return result

    return wrapper


def async_profile_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()

        result = await func(*args, **kwargs)

        pr.disable()

        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats(SortKey.CUMULATIVE)
        ps.dump_stats("profile.txt")

        print(f"Profiling results for {func.__name__}:")
        print(s.getvalue())

        return result

    return wrapper


@async_profile_decorator
async def profiled_main(repo_path, saved_graph_path: Path):
    fg = FileGraph.from_repo(Path(repo_path))

    return fg  # or whatever you want to return from main


def construct_edge_series(graph: MultiDiGraph):
    edge_series = []
    visited_edges = set()

    def is_call_to_edge(node, neighbor):
        return any(
            [
                True
                for _, v, attrs in graph.out_edges(node, data=True)
                if v == neighbor and attrs["kind"] == "CallTo"
            ]
        )

    def dfs_edge(current_node, path):
        for neighbor in graph.successors(current_node):
            if is_call_to_edge(current_node, neighbor):
                edge = (current_node, neighbor)
                if edge not in visited_edges:
                    visited_edges.add(edge)
                    new_path = path + [neighbor]

                    # If the neighbor has no other unvisited outgoing 'CallTo' edges, add the path
                    if all(
                        (neighbor, n) in visited_edges
                        or not is_call_to_edge(neighbor, n)
                        for n in graph.successors(neighbor)
                    ):
                        edge_series.append(new_path)
                    else:
                        dfs_edge(neighbor, new_path)

    # Start DFS from each node that has unvisited outgoing 'CallTo' edges
    for node in graph.nodes():
        if any(
            (node, neighbor) not in visited_edges and is_call_to_edge(node, neighbor)
            for neighbor in graph.successors(node)
        ):
            dfs_edge(node, [node])

    return edge_series


@click.group()
def cli():
    """RTFS CLI tool for repository analysis."""
    pass


@cli.command()
@click.argument(
    "repo_path", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option("--saved-graph-path", type=click.Path(), default=None)
def file_graph(repo_path, saved_graph_path):
    """Generate a FileGraph from the repository."""
    fg = FileGraph.from_repo(Path(repo_path))
    click.echo("FileGraph generated successfully.")


@cli.command()
@sync_profile_decorator
@click.argument(
    "repo_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option("--test-run", is_flag=True)
@click.option("--output-format", type=click.Choice(["str", "json"]), default="str")
@click.option("--output-file", type=click.Path(), default=None)
def chunk_graph(repo_path, test_run, output_format, output_file):  # Modified line
    """Generate and manipulate ChunkGraph."""
    # saved_graph_path = Path(GRAPH_FOLDER, Path(repo_path).name + ".jsonffff")
    # if saved_graph_path.exists():
    #     with open(saved_graph_path, "r") as f:
    #         graph_dict = json.loads(f.read())

    #     print("Loading graph from saved file")
    #     cg = ChunkGraph.from_json(Path(repo_path), graph_dict)
    # else:
    cg = chunk(repo_path)
    cg.cluster()
    # cg.to_json(saved_graph_path)

    summarizer = Summarizer()
    asyncio.run(summarizer.summarize(cg, user_confirm=True, test_run=test_run))

    if output_format == "str":
        click.echo(cg.clusters_to_str())
    elif output_format == "json":
        clusters_json = cg.clusters_to_json()
        if output_file:
            with open(output_file, "w") as f:
                json.dump(clusters_json, f, indent=2)
            click.echo(f"Clusters JSON written to {output_file}")
        else:
            click.echo(json.dumps(clusters_json, indent=2))

    # cg.to_json(saved_graph_path)

    click.echo("ChunkGraph generated and processed successfully.")


if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        click.echo(f"Error: {e}")
        traceback.print_exc()
        raise e
