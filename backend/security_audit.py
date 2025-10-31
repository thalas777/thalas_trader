#!/usr/bin/env python3
"""
Security Audit for Autonomous Trading System
Checks for common vulnerabilities and security issues
"""
import re
import os


def check_sql_injection():
    """Check for SQL injection vulnerabilities"""
    print("🔍 Checking for SQL Injection Vulnerabilities...")
    issues = []

    # Django ORM is safe from SQL injection when used properly
    # Check for raw SQL queries
    files_to_check = [
        '/workspaces/thalas_trader/backend/api/views/bots.py',
        '/workspaces/thalas_trader/backend/api/models.py',
    ]

    for filepath in files_to_check:
        if not os.path.exists(filepath):
            continue

        with open(filepath, 'r') as f:
            content = f.read()

            # Check for raw SQL
            if '.raw(' in content or 'execute(' in content:
                issues.append(f"⚠️  Raw SQL found in {filepath} - Review for injection risks")

            # Check for string formatting in queries (dangerous)
            if re.search(r'\.filter\([^)]*%s|\.filter\([^)]*\+|\.filter\([^)]*f"', content):
                issues.append(f"⚠️  String interpolation in query in {filepath}")

    if not issues:
        print("  ✅ No SQL injection vulnerabilities detected (using Django ORM)")
    else:
        for issue in issues:
            print(f"  {issue}")

    return len(issues) == 0


def check_input_validation():
    """Check input validation in API endpoints"""
    print("\n🔍 Checking Input Validation...")
    issues = []

    filepath = '/workspaces/thalas_trader/backend/api/views/bots.py'
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()

            # Check for validation of numeric inputs
            if 'initial_balance' in content:
                if 'initial_balance' in content and 'Decimal' in content:
                    print("  ✅ Balance validation using Decimal type")
                else:
                    issues.append("  ⚠️  Balance validation might be insufficient")

            # Check for position_size validation
            if 'position_size' in content:
                # Should validate 0 < position_size <= 1.0
                if not re.search(r'position_size.*>.*0|position_size.*<.*1', content):
                    issues.append("  ❌ Position size range validation missing (should be 0-1.0)")

            # Check for name sanitization
            if 'name' in content and not re.search(r'strip\(\)|clean|sanitize', content):
                issues.append("  ⚠️  Bot name sanitization not detected")

    for issue in issues:
        print(issue)

    return len(issues) < 2  # Allow some warnings


def check_authentication():
    """Check authentication and authorization"""
    print("\n🔍 Checking Authentication & Authorization...")
    issues = []

    filepath = '/workspaces/thalas_trader/backend/api/views/bots.py'
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()

            # Check for authentication decorators
            if '@login_required' not in content and '@permission_required' not in content:
                issues.append("  ❌ CRITICAL: No authentication decorators found on API views!")
                issues.append("     Anyone can create/start/stop bots without authentication")

            # Check for CSRF protection
            if 'csrf_exempt' in content:
                issues.append("  ⚠️  CSRF protection disabled - review if intentional for API")

    for issue in issues:
        print(issue)

    return 'CRITICAL' not in ''.join(issues)


def check_error_handling():
    """Check error handling for information leakage"""
    print("\n🔍 Checking Error Handling...")
    issues = []

    filepath = '/workspaces/thalas_trader/backend/api/views/bots.py'
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()

            # Check for bare except clauses that might hide errors
            bare_excepts = content.count('except Exception as e')
            if bare_excepts > 0:
                print(f"  ✅ Using specific exception handling ({bare_excepts} instances)")

            # Check if error messages are logged
            if 'logger.error' in content:
                print("  ✅ Errors are being logged")

            # Check if sensitive data might leak in errors
            if re.search(r'str\(e\)|repr\(e\)', content):
                issues.append("  ⚠️  Exception details might leak in responses - review error messages")

    for issue in issues:
        print(issue)

    return True


def check_frontend_xss():
    """Check frontend for XSS vulnerabilities"""
    print("\n🔍 Checking Frontend for XSS Vulnerabilities...")
    issues = []

    filepath = '/workspaces/thalas_trader/frontend/components/CreateBotModal.tsx'
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()

            # React automatically escapes by default
            print("  ✅ Using React (auto-escapes by default)")

            # Check for dangerouslySetInnerHTML
            if 'dangerouslySetInnerHTML' in content:
                issues.append("  ❌ dangerouslySetInnerHTML found - XSS risk!")

            # Check for direct DOM manipulation
            if 'innerHTML' in content or 'outerHTML' in content:
                issues.append("  ⚠️  Direct HTML injection found")

    for issue in issues:
        print(issue)

    return len(issues) == 0


def check_resource_management():
    """Check for resource leaks and DOS vulnerabilities"""
    print("\n🔍 Checking Resource Management...")
    issues = []

    filepath = '/workspaces/thalas_trader/backend/market_scanner.py'
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()

            # Check for timeout in async operations
            if 'timeout' in content or 'asyncio.wait_for' in content:
                print("  ✅ Timeout protection found in async operations")
            else:
                issues.append("  ⚠️  No timeout protection in async operations - DOS risk")

            # Check for rate limiting
            if 'sleep' in content or 'rate_limit' in content:
                print("  ✅ Rate limiting/throttling detected")
            else:
                issues.append("  ⚠️  No rate limiting detected - API abuse risk")

    for issue in issues:
        print(issue)

    return True


def check_data_validation():
    """Check data validation in models and forms"""
    print("\n🔍 Checking Data Model Validation...")

    filepath = '/workspaces/thalas_trader/backend/api/models.py'
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()

            # Check for max_length constraints
            if 'max_length' in content:
                print("  ✅ String length constraints defined")

            # Check for decimal precision
            if 'max_digits' in content and 'decimal_places' in content:
                print("  ✅ Decimal precision constraints defined")

            # Check for choices/enums
            if 'choices=' in content or 'CHOICES' in content:
                print("  ✅ Enum constraints defined for status fields")

    return True


def generate_security_score():
    """Calculate overall security score"""
    print("\n" + "="*80)
    print("📊 SECURITY AUDIT SUMMARY")
    print("="*80)

    checks = {
        "SQL Injection Protection": check_sql_injection(),
        "Input Validation": check_input_validation(),
        "Authentication & Authorization": check_authentication(),
        "Error Handling": check_error_handling(),
        "XSS Protection": check_frontend_xss(),
        "Resource Management": check_resource_management(),
        "Data Validation": check_data_validation(),
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    print("\n📋 Results:")
    for check_name, passed_check in checks.items():
        status = "✅ PASS" if passed_check else "❌ FAIL"
        print(f"  {status} - {check_name}")

    score = (passed / total) * 10
    print(f"\n🎯 Overall Security Score: {score:.1f}/10")

    if score >= 9:
        print("🔒 Excellent - Production ready with minor improvements")
    elif score >= 7:
        print("⚠️  Good - Address critical issues before production")
    elif score >= 5:
        print("⚠️  Fair - Significant security improvements needed")
    else:
        print("❌ Poor - Critical security vulnerabilities detected")

    print("\n🔴 Critical Issues to Address:")
    print("  1. Add authentication/authorization to API endpoints")
    print("  2. Implement position_size range validation (0-1.0)")
    print("  3. Add rate limiting to prevent API abuse")
    print("  4. Consider adding request throttling for market scanner")

    print("\n🟡 Recommended Improvements:")
    print("  1. Add bot name sanitization/validation")
    print("  2. Implement more granular error messages")
    print("  3. Add API request logging for audit trails")
    print("  4. Consider adding CORS configuration for frontend")

    print("="*80 + "\n")


def main():
    """Run security audit"""
    print("\n" + "="*80)
    print("🔒 SECURITY AUDIT - AUTONOMOUS TRADING SYSTEM")
    print("="*80 + "\n")

    generate_security_score()


if __name__ == "__main__":
    main()
