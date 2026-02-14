from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.buyer import Buyer


class BuyerService:
    @staticmethod
    async def get_or_create(
        session: AsyncSession, fb_name: str, fb_profile_url: str | None = None
    ) -> Buyer:
        """Get existing buyer by name or create a new one."""
        result = await session.execute(
            select(Buyer).where(Buyer.fb_name == fb_name)
        )
        buyer = result.scalar_one_or_none()

        if buyer:
            if fb_profile_url and not buyer.fb_profile_url:
                buyer.fb_profile_url = fb_profile_url
                await session.commit()
            return buyer

        buyer = Buyer(fb_name=fb_name, fb_profile_url=fb_profile_url)
        session.add(buyer)
        await session.commit()
        await session.refresh(buyer)
        return buyer
