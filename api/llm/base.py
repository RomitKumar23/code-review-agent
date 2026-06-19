from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ReviewContext:
    repo: str
    pr_number: int
    pr_title: str
    language: Optional[str] = None   # detected from file extensions

@dataclass
class ReviewComment:
    file: str
    line: int
    severity: str          # "error" | "warning" | "suggestion"
    message: str
    suggestion: Optional[str] = None   # optional code fix

@dataclass
class ReviewResult:
    summary: str
    comments: list[ReviewComment]
    provider_used: str
    model_used: str
    tokens_used: int

class BaseLLMProvider(ABC):
    @abstractmethod
    async def review(self, diff: str, ctx: ReviewContext) -> ReviewResult:
        ...

    def _build_prompt(self, diff: str, ctx: ReviewContext) -> str:
        return f"""You are an expert code reviewer. Review this pull request diff.
                Repository: {ctx.repo}
                PR #{ctx.pr_number}: {ctx.pr_title}

                Respond ONLY with valid JSON in this exact structure:
                {{
                "summary": "one paragraph overall assessment",
                "comments": [   
                    {{
                    "file": "path/to/file.py",
                    "line": 42,
                    "severity": "error|warning|suggestion",
                    "message": "what the issue is and why it matters",
                    "suggestion": "optional: what to write instead"
                    }}
                ]
                }}

                Diff to review:
                {diff}"""
