from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
import re


class RepoCreate(BaseModel):
    url: str
    owner: Optional[str] = None
    repo_name: Optional[str] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v:
            raise ValueError("URL is required")

        patterns = [
            r"^https?://github\.com/([\w.-]+)/([\w.-]+)\.git?$",
            r"^git@github\.com:([\w.-]+)/([\w.-]+)(?:\.git)?$",
        ]

        if not any(re.match(pattern, v) for pattern in patterns):
            raise ValueError(
                "Invalid GitHub URL format. Must be either HTTP(S) or SSH form."
            )

        return v

    @model_validator(mode="after")
    def extract_info(self) -> "RepoCreate":
        if self.owner is None or self.repo_name is None:
            match = re.match(
                r"(?:https?://github\.com/|git@github\.com:)([\w.-]+)/([\w.-]+?)(?:\.git)?$",
                self.url,
            )

            if match:
                self.owner = self.owner or match.group(1)
                self.repo_name = self.repo_name or match.group(2)
            else:
                raise ValueError("Could not extract owner and repo_name from URL")

        return self


repo = RepoCreate(url="https://github.com/microsoft/promptflow.git")
print(repo)