import requests
import re
from pathlib import Path
from src.config import REPOS_ROOT, INDEX_ROOT, GRAPH_ROOT

def get_repo_size(owner, repo, token):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)
    print(owner, repo, token)

    if response.status_code == 200:
        data = response.json()
        size_kb = data['size']
        size_mb = size_kb / 1024
        return size_mb
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return f"Error: {response.status_code}, {response.text}"
    
def get_repo_main_language(owner, repo, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/languages"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        languages = response.json()
        if languages:
            # The first key in the dictionary is the most used language
            main_language = next(iter(languages))
            return main_language
        else:
            return "No language detected"
    else:
        return f"Error: {response.status_code}, {response.text}"

def http_to_ssh(url):
    """Convert HTTP(S) URL to SSH URL."""
    match = re.match(r"https?://(?:www\.)?github\.com/(.+)/(.+)\.git", url)
    if match:
        return f"git@github.com:{match.group(1)}/{match.group(2)}.git"
    return url  # Return original if not a GitHub HTTP(S) URL

def repo_path(owner: str, repo_name: str) -> Path:
    return Path(REPOS_ROOT) / (owner + "_" + repo_name)

def index_path(owner: str, repo_name: str) -> Path:
    return Path(INDEX_ROOT) / (owner + "_" + repo_name)

def graph_path(owner: str, repo_name: str) -> Path:
    return Path(GRAPH_ROOT) / (owner + "_" + repo_name)