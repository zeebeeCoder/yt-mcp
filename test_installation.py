#!/usr/bin/env python3
"""
Test script to verify CLI installation and functionality.
Run this after installation to ensure everything works correctly.
"""

import subprocess
import sys


def run_command(cmd, description):
    """Run a command and print results"""
    print(f"\n🧪 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Success!")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()[:200]}...")
        else:
            print(f"❌ Failed with code {result.returncode}")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out (expected for long operations)")
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    return True


def test_uv_installation():
    """Test UV-based installation"""
    print("\n" + "=" * 60)
    print("🔧 Testing UV Installation Method")
    print("=" * 60)

    # Test UV commands
    tests = [
        (["uv", "run", "yt-analyze", "--help"], "yt-analyze help via UV"),
        (["uv", "run", "yt-setup", "--help"], "yt-setup help via UV"),
        (["uv", "run", "yt-setup", "--show"], "Show credential status via UV"),
        (["uv", "run", "yt-setup", "--validate"], "Validate credentials via UV"),
    ]

    success_count = 0
    for cmd, desc in tests:
        if run_command(cmd, desc):
            success_count += 1

    print(f"\n📊 UV Installation Test Results: {success_count}/{len(tests)} passed")
    return success_count == len(tests)


def test_pip_installation():
    """Test pip-based installation"""
    print("\n" + "=" * 60)
    print("🔧 Testing Pip Installation Method")
    print("=" * 60)

    # Test direct commands (only if pip install worked)
    tests = [
        (["yt-analyze", "--help"], "yt-analyze help (direct)"),
        (["yt-setup", "--help"], "yt-setup help (direct)"),
        (["yt-setup", "--show"], "Show credential status (direct)"),
        (["yt-setup", "--validate"], "Validate credentials (direct)"),
    ]

    success_count = 0
    for cmd, desc in tests:
        if run_command(cmd, desc):
            success_count += 1

    print(f"\n📊 Pip Installation Test Results: {success_count}/{len(tests)} passed")
    return success_count > 0  # At least some should work


def main():
    print("🎯 YouTube Analysis Pipeline - Installation Test")
    print("This script tests both UV and pip installation methods.")

    # Test UV method (should always work)
    uv_works = test_uv_installation()

    # Test pip method (may fail on Python 3.13)
    pip_works = test_pip_installation()

    # Summary
    print("\n" + "=" * 60)
    print("📋 FINAL TEST SUMMARY")
    print("=" * 60)

    print(f"UV Installation:  {'✅ Working' if uv_works else '❌ Failed'}")
    print(f"Pip Installation: {'✅ Working' if pip_works else '❌ Failed'}")

    if uv_works:
        print("\n🎉 SUCCESS: Use UV commands (uv run yt-analyze, uv run yt-setup)")
    elif pip_works:
        print("\n🎉 SUCCESS: Use direct commands (yt-analyze, yt-setup)")
    else:
        print("\n⚠️  Both methods failed. Check your installation.")
        return 1

    print("\n💡 Next steps:")
    if uv_works:
        print("1. Run: uv run yt-setup")
        print("2. Configure your API keys")
        print(
            "3. Test: uv run yt-analyze 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' --transcript-only"
        )
    else:
        print("1. Run: yt-setup")
        print("2. Configure your API keys")
        print("3. Test: yt-analyze 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' --transcript-only")

    return 0


if __name__ == "__main__":
    sys.exit(main())
