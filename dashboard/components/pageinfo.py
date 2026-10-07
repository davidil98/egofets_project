from dataclasses import dataclass


@dataclass
class PageInfo:
    route: str
    modulepath: str
    classname: str
    display: str

    @property
    def folder(self) -> str:
        parts = self.route.strip('/').split('/')
        return 'pages_root' if len(parts) == 1 else parts[0]
