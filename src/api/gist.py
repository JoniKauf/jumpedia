import typing as t
import requests
from ..database import secret

__TOKEN = secret.listen().GITHUB_GIST_TOKEN

class _FileContentT(t.TypedDict):
    content: str

def create_gist(files: dict[str, _FileContentT], /, description: str | None = None, public: bool = False):
    url: str = "https://api.github.com/gists"
    headers: dict[str, str] = {
        'Authorization': f"token {__TOKEN}",
        'Accept': "application/vnd.github+json"
    }

    payload: dict[str, t.Any] = {'public': public}

    if description is not None:
        payload['description'] = description
    
    payload['files'] = files

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 201:
        gist_url: str = response.json().get("html_url")
        return gist_url
    else:
        raise Exception(f"Failed to create gist: {response.status_code}\n{response.text}")



def __main() -> None:
    ESCAPE: set[str] = {
        '\\', '`'
    }

    TRANS_TABLE = str.maketrans({
        char: '\\' + char
        for char in ESCAPE
    })

    DELIM: str = '|'

    def table_to_markdown(table: t.Sequence[t.Sequence[str]], /, headers: t.Sequence[str] = (), *, soft_split_limit: int = 500_000) -> list[str]:
        result: list[str] = []

        curr_rows: list[str] = []
        char_count: int = 0
        
        if headers:
            curr_rows.append(DELIM.join(headers))
            curr_rows.append(DELIM.join(tuple(':---' for _ in headers)))
        
        for row in table:
            cells: list[str] = []

            for cell in row:
                cell = f"`{cell.translate(TRANS_TABLE)}`"
                cells.append(cell)
            
            new_row = DELIM.join(cells)
            char_count += len(new_row)
            curr_rows.append(new_row)

            if char_count >= soft_split_limit:
                result.append('\n'.join(curr_rows))
                curr_rows.clear()
                char_count = 0
        
        if curr_rows:
            result.append('\n'.join(curr_rows))

        return result
    
    
    HEADERS = [str(i) for i in range(32)]
    CHARS = tuple(ESCAPE | set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!§$%&/=²³'))
    table: list[list[str]] = []

    import random

    for _ in range(5000):
        row: list[str] = []

        for _ in HEADERS:
            cell: list[str] = []

            for _ in range(random.randint(1, 10)):
                cell.append(random.choice(CHARS))
            
            row.append(''.join(cell))
        
        table.append(row.copy())

    markdowns = table_to_markdown(table, HEADERS)

    for i, md in enumerate(markdowns[1:]):
        markdowns[i] = f"{DELIM.join(HEADERS)}\n{DELIM.join(":---" for _ in HEADERS)}\n{md}"

    files: dict[str, _FileContentT] = {
        f'test{i}.md': {'content': md} 
        for i, md in enumerate(markdowns, start=1)
    }
    
    print(
        create_gist(
            files,
            "A very cool test to show gummy!"
        )
    )
    
if __name__ == '__main__':
    __main()