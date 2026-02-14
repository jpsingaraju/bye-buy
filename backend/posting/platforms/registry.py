from typing import Dict, Type
from .base import PlatformPoster


class PlatformRegistry:
    """Registry for platform posters."""

    _posters: Dict[str, Type[PlatformPoster]] = {}

    @classmethod
    def register(cls, platform_name: str):
        """Decorator to register a platform poster."""
        def decorator(poster_class: Type[PlatformPoster]):
            cls._posters[platform_name] = poster_class
            return poster_class
        return decorator

    @classmethod
    def get_poster(cls, platform_name: str) -> PlatformPoster:
        """Get an instance of the poster for the given platform."""
        if platform_name not in cls._posters:
            raise ValueError(f"Unknown platform: {platform_name}")
        return cls._posters[platform_name]()

    @classmethod
    def list_platforms(cls) -> list[str]:
        """List all registered platforms."""
        return list(cls._posters.keys())
