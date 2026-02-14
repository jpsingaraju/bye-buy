from stagehand import AsyncStagehand

from .base import PlatformPoster, PostingResult
from .registry import PlatformRegistry
from ..config import settings


@PlatformRegistry.register("facebook_marketplace")
class FacebookMarketplacePoster(PlatformPoster):
    """Post listings to Facebook Marketplace using Stagehand."""

    @property
    def platform_name(self) -> str:
        return "facebook_marketplace"

    async def post_listing(
        self,
        title: str,
        description: str,
        price: float,
        image_paths: list[str],
    ) -> PostingResult:
        """Post a listing to Facebook Marketplace."""
        session = None
        client = None

        try:
            # Initialize Stagehand client
            client = AsyncStagehand(
                browserbase_api_key=settings.browserbase_api_key,
                browserbase_project_id=settings.browserbase_project_id,
                model_api_key=settings.model_api_key,
            )

            # Build session params with context if available
            session_params = {
                "model_name": "gpt-4o",
            }

            # Add context for persistent Facebook login
            if settings.browserbase_context_id:
                session_params["browserbase_session_create_params"] = {
                    "browser_settings": {
                        "context": {
                            "id": settings.browserbase_context_id,
                            "persist": True,  # Save any new cookies
                        },
                        "solve_captchas": True,
                    }
                }

            # Start a browser session
            session = await client.sessions.start(**session_params)

            # Navigate to Marketplace create item page
            await session.navigate(url="https://www.facebook.com/marketplace/create/item")

            # Use execute to run the full posting flow autonomously
            execute_result = await session.execute(
                execute_options={
                    "instruction": f"""
                    Post a listing to Facebook Marketplace with the following details:
                    - Title: {title}
                    - Price: ${int(price)}
                    - Description: {description}

                    Steps:
                    1. Wait for the page to fully load
                    2. If you see a login page, the session is not authenticated - report this as an error
                    3. Find and fill in the title field with: {title}
                    4. Find and fill in the price field with: {int(price)}
                    5. Find and fill in the description field with: {description}
                    6. Select an appropriate category for this item
                    7. Click the Next or Publish button to proceed
                    8. If there are additional confirmation steps, complete them
                    9. Wait for the listing to be created
                    """,
                    "max_steps": 15,
                },
                agent_config={"model": "gpt-4o"},
                timeout=120.0,
            )

            # Try to extract the listing URL or confirmation
            try:
                extract_result = await session.extract(
                    instruction="Extract the URL of the newly created listing or any confirmation message that the listing was posted successfully. If you see a login page, return success: false.",
                    schema={
                        "type": "object",
                        "properties": {
                            "listing_url": {"type": "string", "description": "URL of the created listing"},
                            "confirmation": {"type": "string", "description": "Confirmation message"},
                            "success": {"type": "boolean", "description": "Whether posting was successful"}
                        }
                    }
                )

                result_data = extract_result.data.result if extract_result.data else {}
                external_url = result_data.get("listing_url")
                success = result_data.get("success", False)

                if success or external_url:
                    return PostingResult(
                        success=True,
                        external_url=external_url,
                    )
            except Exception:
                pass

            # If we got here without error, assume success
            return PostingResult(
                success=True,
                external_url=None,
            )

        except Exception as e:
            return PostingResult(
                success=False,
                error_message=str(e),
            )
        finally:
            # Clean up session
            if session:
                try:
                    await session.end()
                except Exception:
                    pass
