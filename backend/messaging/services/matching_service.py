import logging
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.listing import Listing

logger = logging.getLogger(__name__)


class MatchingService:
    MATCH_THRESHOLD = 0.5

    @staticmethod
    async def match_listing(
        session: AsyncSession, listing_title_from_chat: str
    ) -> Listing | None:
        """Fuzzy-match a chat listing title to the closest active listing in the DB."""
        if not listing_title_from_chat:
            return None

        result = await session.execute(
            select(Listing).where(Listing.status == "active")
        )
        listings = result.scalars().all()

        if not listings:
            return None

        best_match = None
        best_score = 0.0
        query_lower = listing_title_from_chat.lower().strip()

        for listing in listings:
            score = SequenceMatcher(
                None, query_lower, listing.title.lower().strip()
            ).ratio()

            if score > best_score:
                best_score = score
                best_match = listing

        if best_score >= MatchingService.MATCH_THRESHOLD and best_match:
            logger.info(
                f"Matched '{listing_title_from_chat}' → '{best_match.title}' "
                f"(score: {best_score:.2f})"
            )
            return best_match

        logger.warning(
            f"No match for '{listing_title_from_chat}' (best: {best_score:.2f})"
        )
        return None
