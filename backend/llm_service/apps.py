from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class LlmServiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "llm_service"

    def ready(self):
        """
        Initialize LLM providers when Django starts

        This method is called once Django is ready and all apps are loaded.
        It initializes the provider registry from environment variables.
        """
        # Only initialize in the main process, not during migrations
        import sys
        if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
            try:
                from .provider_factory import initialize_providers

                logger.info("Initializing LLM providers from environment variables")
                registry = initialize_providers()

                # Log initialization status
                status = registry.get_registry_status()
                logger.info(
                    f"LLM Service ready: {status['total_providers']} providers registered, "
                    f"{status['available_providers']} available"
                )

            except Exception as e:
                logger.error(f"Failed to initialize LLM providers: {e}", exc_info=True)
