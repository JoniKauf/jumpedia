import typing as t

import requests

from . import secret

__TOKEN = secret.listen().GITHUB_GIST_TOKEN
API_URL: str = "https://api.github.com/gists"


class _FileContentT(t.TypedDict):
    content: str


def create_gist(
    files: dict[str, str],
    /,
    description: str | None = None,
    public: bool = False,
) -> str:

    headers: dict[str, str] = {
        "Authorization": f"token {__TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    payload: dict[str, t.Any] = {"public": public}

    if description is not None:
        payload["description"] = description

    payload["files"] = {
        file_name: {"content": content} for file_name, content in files.items()
    }

    response = requests.post(API_URL, json=payload, headers=headers)

    if response.status_code == 201:
        gist_url: str = response.json().get("html_url")
        return gist_url
    else:
        raise Exception(
            f"Failed to create gist: {response.status_code}\n{response.text}"
        )
