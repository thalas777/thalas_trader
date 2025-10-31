#!/usr/bin/env python
"""
API Test Script for Thalas Trader Backend

This script tests all API endpoints to verify functionality.
Run after starting the Django server: python manage.py runserver
"""
import requests
import json
from typing import Dict, Any
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

BASE_URL = "http://localhost:8000/api/v1"


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Fore.CYAN}{'=' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{text.center(70)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 70}{Style.RESET_ALL}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_error(text: str):
    """Print error message"""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def print_info(text: str):
    """Print info message"""
    print(f"{Fore.YELLOW}ℹ {text}{Style.RESET_ALL}")


def print_json(data: Dict[Any, Any], indent: int = 2):
    """Pretty print JSON data"""
    print(f"{Fore.WHITE}{json.dumps(data, indent=indent)}{Style.RESET_ALL}")


def test_endpoint(method: str, endpoint: str, expected_status: int = 200, data: Dict = None):
    """
    Test an API endpoint

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        expected_status: Expected HTTP status code
        data: Optional request body for POST requests

    Returns:
        Response object or None if failed
    """
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{Fore.MAGENTA}Testing: {method} {endpoint}{Style.RESET_ALL}")

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            print_error(f"Unsupported method: {method}")
            return None

        print(f"Status Code: {response.status_code}")

        if response.status_code == expected_status:
            print_success(f"Status {response.status_code} (Expected {expected_status})")
        else:
            print_error(
                f"Status {response.status_code} (Expected {expected_status})"
            )

        # Try to parse JSON response
        try:
            json_data = response.json()
            print("\nResponse:")
            print_json(json_data)
            return response
        except json.JSONDecodeError:
            print(f"Response (non-JSON): {response.text}")
            return response

    except requests.exceptions.ConnectionError:
        print_error("Connection failed. Is the server running?")
        print_info("Start server with: python manage.py runserver")
        return None
    except requests.exceptions.Timeout:
        print_error("Request timed out")
        return None
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return None


def main():
    """Run all API tests"""
    print_header("THALAS TRADER BACKEND API TESTS")

    # Test 1: Summary endpoint
    print_header("Test 1: Summary Endpoint")
    test_endpoint("GET", "/summary")

    # Test 2: Bots list
    print_header("Test 2: Bots List Endpoint")
    test_endpoint("GET", "/bots")

    # Test 3: Bot detail
    print_header("Test 3: Bot Detail Endpoint")
    test_endpoint("GET", "/bots/1")

    # Test 4: Bot detail (not found)
    print_header("Test 4: Bot Detail (Not Found)")
    test_endpoint("GET", "/bots/999", expected_status=404)

    # Test 5: Start bot
    print_header("Test 5: Start Bot")
    test_endpoint("POST", "/bots/1/start")

    # Test 6: Stop bot
    print_header("Test 6: Stop Bot")
    test_endpoint("POST", "/bots/1/stop")

    # Test 7: Trades list
    print_header("Test 7: Trades List")
    test_endpoint("GET", "/trades")

    # Test 8: Trades with pagination
    print_header("Test 8: Trades with Pagination")
    test_endpoint("GET", "/trades?limit=5&offset=0")

    # Test 9: Trade detail
    print_header("Test 9: Trade Detail")
    test_endpoint("GET", "/trades/1")

    # Test 10: Performance data
    print_header("Test 10: Performance Data")
    test_endpoint("GET", "/performance")

    # Test 11: LLM health check
    print_header("Test 11: LLM Service Health Check")
    test_endpoint("GET", "/strategies/llm")

    # Test 12: LLM signal generation (with mock data)
    print_header("Test 12: LLM Signal Generation")
    mock_market_data = {
        "market_data": {
            "rsi": 45.2,
            "ema_short": 42500.0,
            "ema_long": 42300.0,
            "volume": 1250000,
            "macd": 120.5,
            "recent_candles": [
                {"open": 42400, "high": 42600, "low": 42300, "close": 42500, "volume": 1200000},
                {"open": 42500, "high": 42700, "low": 42450, "close": 42600, "volume": 1300000},
            ]
        },
        "pair": "BTC/USDT",
        "timeframe": "5m",
        "current_price": 42500.0
    }

    response = test_endpoint("POST", "/strategies/llm", data=mock_market_data)

    # Test 13: LLM signal with missing data (should fail)
    print_header("Test 13: LLM Signal with Missing Data (Error Case)")
    test_endpoint(
        "POST",
        "/strategies/llm",
        expected_status=400,
        data={"pair": "BTC/USDT"}  # Missing market_data
    )

    # Final summary
    print_header("TEST SUMMARY")
    print_info("All API endpoint tests completed!")
    print_info("Check output above for any failures")
    print_info("\nNext steps:")
    print("  1. Review any failed tests")
    print("  2. Configure LLM API keys to test actual LLM integration")
    print("  3. Connect to a real Freqtrade instance to test live data")


if __name__ == "__main__":
    # Check if colorama is installed
    try:
        import colorama
    except ImportError:
        print("Installing colorama for colored output...")
        import subprocess
        subprocess.check_call(["pip", "install", "colorama"])
        import colorama
        from colorama import init, Fore, Style
        init(autoreset=True)

    main()
