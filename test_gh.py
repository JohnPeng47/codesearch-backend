import requests
from starlette.config import Config
import re

token = Config(".env")("GITHUB_API_TOKEN") 

def get_repo_size(owner, repo, token):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        size_kb = data['size']
        size_mb = size_kb / 1024
        return size_mb
    else:
        return f"Error: {response.status_code}, {response.text}"

def extract_owner_and_repo(url):
    # Regular expression pattern to match GitHub URLs
    pattern = r"https?://github\.com/([^/]+)/([^/]+)"
    
    # Try to match the pattern in the URL
    match = re.match(pattern, url)
    
    if match:
        owner = match.group(1)
        repo = match.group(2)
        return owner, repo
    else:
        return None, None  # Return None if the URL doesn't match the expected format


repos = [
    "https://github.com/microsoft/promptflow",
    "https://github.com/scipy/scipy",
    "https://github.com/django/django",
    "https://github.com/Aider-AI/aider",
    "https://github.com/aorwall/moatless-tools"
]

for owner, repo in map(extract_owner_and_repo, repos):
    if owner and repo:
        size = get_repo_size(owner, repo, token)
        if isinstance(size, float):
            print(f"The size of the repository {repo} is {size:.2f} MB")
        else:
            print(size)
    else:
        print("Invalid URL format")