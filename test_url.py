from pydantic import BaseModel, field_validator, ValidationInfo, Field, model_validator
from typing import Optional
import re


class RepoCreate(BaseModel):
    url: str
    owner: Optional[str] = Field(default=None)
    repo_name: Optional[str] = Field(default=None)

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v:
            raise ValueError("URL is required")
        
        http_match = re.match(r"^https?://github\.com/([\w.-]+)/([\w.-]+)$", v)
        ssh_match = re.match(r"^git@github\.com:([\w.-]+)/([\w.-]+)(?:\.git)?$", v)
        
        if not (http_match or ssh_match):
            raise ValueError("Invalid GitHub URL format. Must be either HTTP(S) or SSH form.")
        
        return v

    @model_validator(mode='after')
    def extract_info(self) -> 'RepoCreate':
        http_match = re.match(r"^https?://github\.com/([\w.-]+)/([\w.-]+)$", self.url)
        ssh_match = re.match(r"^git@github\.com:([\w.-]+)/([\w.-]+)(?:\.git)?$", self.url)
        
        if http_match:
            owner, repo_name = http_match.groups()
        elif ssh_match:
            owner, repo_name = ssh_match.groups()
        else:
            raise ValueError(
                "Invalid GitHub URL format. Must be either HTTP(S) or SSH form."
            )

        self.owner = owner
        self.repo_name = repo_name

        return self



test_repo = RepoCreate(url="https://github.com/aorwall/moatless-tools")
print(test_repo)