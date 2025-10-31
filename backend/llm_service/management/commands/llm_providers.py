"""
Django management command for LLM provider management

Usage:
    python manage.py llm_providers --status
    python manage.py llm_providers --enable anthropic
    python manage.py llm_providers --disable grok
    python manage.py llm_providers --test anthropic
    python manage.py llm_providers --health-check
"""
import asyncio
from django.core.management.base import BaseCommand, CommandError
from llm_service.providers import get_registry
from llm_service.provider_factory import ProviderFactory


class Command(BaseCommand):
    help = 'Manage LLM providers (status, enable, disable, test)'

    def add_arguments(self, parser):
        """Add command-line arguments"""
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show status of all providers',
        )
        parser.add_argument(
            '--enable',
            type=str,
            metavar='PROVIDER',
            help='Enable a specific provider',
        )
        parser.add_argument(
            '--disable',
            type=str,
            metavar='PROVIDER',
            help='Disable a specific provider',
        )
        parser.add_argument(
            '--test',
            type=str,
            metavar='PROVIDER',
            help='Test a specific provider with health check',
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Run health check on all providers',
        )
        parser.add_argument(
            '--reinit',
            action='store_true',
            help='Reinitialize all providers from environment',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all available provider types',
        )

    def handle(self, *args, **options):
        """Handle the command"""
        try:
            # List available provider types
            if options['list']:
                self.list_provider_types()
                return

            # Reinitialize providers
            if options['reinit']:
                self.reinitialize_providers()
                return

            # Show status
            if options['status']:
                self.show_status()
                return

            # Enable provider
            if options['enable']:
                self.enable_provider(options['enable'])
                return

            # Disable provider
            if options['disable']:
                self.disable_provider(options['disable'])
                return

            # Test provider
            if options['test']:
                self.test_provider(options['test'])
                return

            # Health check all
            if options['health_check']:
                self.health_check_all()
                return

            # No options provided, show help
            self.stdout.write(self.style.WARNING('No action specified. Use --help for options.'))
            self.show_status()

        except Exception as e:
            raise CommandError(f'Error: {e}')

    def list_provider_types(self):
        """List all available provider types"""
        self.stdout.write(self.style.SUCCESS('\nAvailable Provider Types:'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        for provider_name, provider_class in ProviderFactory.PROVIDER_CLASSES.items():
            default_model = ProviderFactory.DEFAULT_MODELS.get(provider_name, 'N/A')
            self.stdout.write(
                f'  {provider_name:15} -> {provider_class.__name__:25} '
                f'(default: {default_model})'
            )

        self.stdout.write(self.style.WARNING('\nTo configure a provider, set these environment variables:'))
        self.stdout.write('  {PROVIDER}_API_KEY      - API key (required)')
        self.stdout.write('  {PROVIDER}_ENABLED      - Enable/disable (default: true)')
        self.stdout.write('  {PROVIDER}_MODEL        - Model name (optional)')
        self.stdout.write('  {PROVIDER}_WEIGHT       - Consensus weight (default: 1.0)')
        self.stdout.write('  {PROVIDER}_MAX_TOKENS   - Max tokens (default: 1024)')
        self.stdout.write('  {PROVIDER}_TEMPERATURE  - Temperature (default: 0.7)')
        self.stdout.write('  {PROVIDER}_TIMEOUT      - Timeout in seconds (default: 30)')
        self.stdout.write('  {PROVIDER}_MAX_RETRIES  - Max retries (default: 3)')

    def reinitialize_providers(self):
        """Reinitialize all providers from environment"""
        self.stdout.write(self.style.WARNING('\nReinitializing providers from environment...'))

        # Clear registry
        registry = get_registry()
        registry.clear()

        # Reinitialize
        registry = ProviderFactory.initialize_registry()

        status = registry.get_registry_status()
        self.stdout.write(
            self.style.SUCCESS(
                f'\nProviders reinitialized: {status["total_providers"]} total, '
                f'{status["available_providers"]} available'
            )
        )

        # Show status
        self.show_status()

    def show_status(self):
        """Display status of all providers"""
        registry = get_registry()
        status = registry.get_registry_status()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('LLM PROVIDER REGISTRY STATUS'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Overall stats
        self.stdout.write(f'\nTotal Providers: {status["total_providers"]}')
        self.stdout.write(f'Available Providers: {status["available_providers"]}')

        if status.get('providers_by_status'):
            self.stdout.write('\nProviders by Status:')
            for status_name, count in status['providers_by_status'].items():
                self.stdout.write(f'  {status_name}: {count}')

        # Individual provider details
        if not status['provider_names']:
            self.stdout.write(self.style.WARNING('\nNo providers registered!'))
            self.stdout.write(self.style.WARNING('Check your API key configuration in environment variables.'))
            return

        self.stdout.write(self.style.SUCCESS('\n' + '-' * 80))
        self.stdout.write(self.style.SUCCESS('PROVIDER DETAILS'))
        self.stdout.write(self.style.SUCCESS('-' * 80))

        for name in status['provider_names']:
            provider = registry.get_provider(name)
            if provider:
                provider_status = provider.get_status()
                self.display_provider_status(provider_status)

    def display_provider_status(self, status):
        """Display detailed status for a single provider"""
        # Status indicator
        status_color = {
            'active': self.style.SUCCESS,
            'degraded': self.style.WARNING,
            'unavailable': self.style.ERROR,
            'circuit_open': self.style.ERROR,
        }
        color_func = status_color.get(status['status'], self.style.WARNING)

        # Enabled indicator
        enabled_str = 'ENABLED' if status['enabled'] else 'DISABLED'
        enabled_color = self.style.SUCCESS if status['enabled'] else self.style.WARNING

        self.stdout.write(f'\n{status["name"].upper()}:')
        self.stdout.write(f'  Model:        {status["model"]}')
        self.stdout.write(f'  Status:       {color_func(status["status"].upper())}')
        self.stdout.write(f'  Enabled:      {enabled_color(enabled_str)}')
        self.stdout.write(f'  Weight:       {status["weight"]:.2f}')
        self.stdout.write(f'  Requests:     {status["requests"]}')
        self.stdout.write(f'  Errors:       {status["errors"]}')
        self.stdout.write(f'  Error Rate:   {status["error_rate"]:.2%}')
        self.stdout.write(f'  Avg Latency:  {status["avg_latency_ms"]:.2f}ms')

        if status['last_request']:
            self.stdout.write(f'  Last Request: {status["last_request"]}')

        if status['last_error']:
            self.stdout.write(f'  Last Error:   {self.style.ERROR(status["last_error"])}')

    def enable_provider(self, provider_name):
        """Enable a specific provider"""
        registry = get_registry()
        provider = registry.get_provider(provider_name)

        if not provider:
            raise CommandError(f'Provider "{provider_name}" not found')

        if registry.enable_provider(provider_name):
            self.stdout.write(
                self.style.SUCCESS(f'\nProvider "{provider_name}" enabled successfully')
            )
            # Show updated status
            status = provider.get_status()
            self.display_provider_status(status)
        else:
            raise CommandError(f'Failed to enable provider "{provider_name}"')

    def disable_provider(self, provider_name):
        """Disable a specific provider"""
        registry = get_registry()
        provider = registry.get_provider(provider_name)

        if not provider:
            raise CommandError(f'Provider "{provider_name}" not found')

        if registry.disable_provider(provider_name):
            self.stdout.write(
                self.style.WARNING(f'\nProvider "{provider_name}" disabled successfully')
            )
            # Show updated status
            status = provider.get_status()
            self.display_provider_status(status)
        else:
            raise CommandError(f'Failed to disable provider "{provider_name}"')

    def test_provider(self, provider_name):
        """Test a specific provider with health check"""
        registry = get_registry()
        provider = registry.get_provider(provider_name)

        if not provider:
            raise CommandError(f'Provider "{provider_name}" not found')

        self.stdout.write(f'\nTesting provider "{provider_name}"...')

        # Run async health check
        try:
            is_healthy = asyncio.run(provider.health_check())

            if is_healthy:
                self.stdout.write(
                    self.style.SUCCESS(f'\n✓ Provider "{provider_name}" is HEALTHY')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'\n✗ Provider "{provider_name}" is UNHEALTHY')
                )

            # Show updated status
            status = provider.get_status()
            self.display_provider_status(status)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Health check failed: {e}')
            )
            raise CommandError(f'Health check error: {e}')

    def health_check_all(self):
        """Run health check on all providers"""
        registry = get_registry()
        all_providers = registry.get_all_providers()

        if not all_providers:
            self.stdout.write(self.style.WARNING('\nNo providers registered!'))
            return

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('HEALTH CHECK - ALL PROVIDERS'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Run health checks
        results = asyncio.run(registry.health_check_all())

        # Display results
        healthy_count = sum(1 for is_healthy in results.values() if is_healthy)
        total_count = len(results)

        self.stdout.write(f'\nHealth Check Results: {healthy_count}/{total_count} providers healthy\n')

        for provider_name, is_healthy in results.items():
            status_icon = '✓' if is_healthy else '✗'
            status_text = 'HEALTHY' if is_healthy else 'UNHEALTHY'
            color_func = self.style.SUCCESS if is_healthy else self.style.ERROR

            self.stdout.write(
                f'  {status_icon} {provider_name:15} -> {color_func(status_text)}'
            )

        # Show summary
        self.stdout.write(self.style.SUCCESS('\n' + '-' * 80))
        if healthy_count == total_count:
            self.stdout.write(
                self.style.SUCCESS('All providers are healthy!')
            )
        elif healthy_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'{total_count - healthy_count} provider(s) are experiencing issues'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR('All providers are unhealthy!')
            )
