from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class PostingResult:
    success: bool
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    error_message: Optional[str] = None


class PlatformPoster(ABC):
    """Abstract base class for platform-specific posters."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier."""
        pass

    @abstractmethod
    async def post_listing(
        self,
        title: str,
        description: str,
        price: float,
        image_paths: list[str],
        condition: str = "good",
        location: str | None = None,
    ) -> PostingResult:
        """Post a listing to the platform."""
        pass
