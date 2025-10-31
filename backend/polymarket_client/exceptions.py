"""
Custom exceptions for Polymarket API client.

This module defines a hierarchy of exceptions for different error scenarios
when interacting with the Polymarket API.
"""


class PolymarketError(Exception):
    """Base exception for all Polymarket-related errors."""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        """
        Initialize Polymarket error.

        Args:
            message: Error message
            status_code: HTTP status code (if applicable)
            response_data: Response data from API (if applicable)
        """
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)

    def __str__(self):
        """String representation of the error."""
        if self.status_code:
            return f"{self.__class__.__name__} (status {self.status_code}): {self.message}"
        return f"{self.__class__.__name__}: {self.message}"


class PolymarketAuthenticationError(PolymarketError):
    """
    Authentication error with Polymarket API.

    Raised when:
    - API key is missing or invalid
    - Authentication signature is invalid
    - Wallet connection fails
    """
    pass


class PolymarketAPIError(PolymarketError):
    """
    Generic API error from Polymarket.

    Raised when:
    - API returns an error response
    - Server error (5xx status codes)
    - Unexpected response format
    """
    pass


class PolymarketRateLimitError(PolymarketError):
    """
    Rate limit exceeded error.

    Raised when:
    - Too many requests in a given time period
    - Rate limit headers indicate throttling
    """

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        response_data: dict = None,
        retry_after: int = None
    ):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            status_code: HTTP status code (default 429)
            response_data: Response data from API
            retry_after: Seconds to wait before retrying
        """
        super().__init__(message, status_code, response_data)
        self.retry_after = retry_after


class PolymarketTimeoutError(PolymarketError):
    """
    Request timeout error.

    Raised when:
    - API request times out
    - Connection timeout
    - Read timeout
    """
    pass


class PolymarketValidationError(PolymarketError):
    """
    Data validation error.

    Raised when:
    - Request data is invalid
    - Response data doesn't match expected schema
    - Required fields are missing
    """
    pass


class PolymarketInsufficientFundsError(PolymarketError):
    """
    Insufficient funds error.

    Raised when:
    - Wallet balance is insufficient for order
    - Collateral requirements not met
    """
    pass


class PolymarketMarketNotFoundError(PolymarketError):
    """
    Market not found error.

    Raised when:
    - Market ID doesn't exist
    - Market has been closed or removed
    """
    pass


class PolymarketOrderError(PolymarketError):
    """
    Order-related error.

    Raised when:
    - Order placement fails
    - Order cancellation fails
    - Invalid order parameters
    """
    pass
