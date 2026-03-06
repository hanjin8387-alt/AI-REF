"""API package.

Compatibility note:
- Router composition lives in `app.main`.
- Keep this package import side-effect free so tests and tools can import
  `app.api.<module>` without constructing aggregate routers.
"""

__all__: list[str] = []
