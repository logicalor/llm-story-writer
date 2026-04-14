"""Chapter generation service."""

from ..interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_loader import PromptLoader


class ChapterService:
    """Service for generating story chapters."""

    def __init__(
        self,
        model_provider: ModelProvider,
        config: Dict[str, Any],
        prompt_loader: PromptLoader,
    ):
        self.model_provider = model_provider
        self.config = config
        self.prompt_loader = prompt_loader
