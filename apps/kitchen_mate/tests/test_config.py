"""Tests for configuration module."""

from __future__ import annotations

from kitchen_mate.config import is_ip_allowed


def test_is_ip_allowed_none_blocks_all() -> None:
    """Test that None allowed_ips blocks all IPs."""
    assert is_ip_allowed("192.168.1.1", None) is False
    assert is_ip_allowed("10.0.0.1", None) is False
    assert is_ip_allowed("127.0.0.1", None) is False


def test_is_ip_allowed_single_ip() -> None:
    """Test matching a single IP address."""
    assert is_ip_allowed("192.168.1.1", "192.168.1.1") is True
    assert is_ip_allowed("192.168.1.2", "192.168.1.1") is False


def test_is_ip_allowed_multiple_ips() -> None:
    """Test matching multiple IP addresses."""
    allowed = "192.168.1.1,10.0.0.1,127.0.0.1"
    assert is_ip_allowed("192.168.1.1", allowed) is True
    assert is_ip_allowed("10.0.0.1", allowed) is True
    assert is_ip_allowed("127.0.0.1", allowed) is True
    assert is_ip_allowed("172.16.0.1", allowed) is False


def test_is_ip_allowed_cidr_range() -> None:
    """Test matching CIDR ranges."""
    allowed = "192.168.1.0/24"
    assert is_ip_allowed("192.168.1.1", allowed) is True
    assert is_ip_allowed("192.168.1.254", allowed) is True
    assert is_ip_allowed("192.168.2.1", allowed) is False


def test_is_ip_allowed_mixed_ips_and_cidr() -> None:
    """Test matching a mix of IPs and CIDR ranges."""
    allowed = "10.0.0.1,192.168.1.0/24,172.16.0.0/16"
    assert is_ip_allowed("10.0.0.1", allowed) is True
    assert is_ip_allowed("192.168.1.100", allowed) is True
    assert is_ip_allowed("172.16.5.10", allowed) is True
    assert is_ip_allowed("8.8.8.8", allowed) is False


def test_is_ip_allowed_with_spaces() -> None:
    """Test that spaces around IPs are handled correctly."""
    allowed = " 192.168.1.1 , 10.0.0.1 "
    assert is_ip_allowed("192.168.1.1", allowed) is True
    assert is_ip_allowed("10.0.0.1", allowed) is True


def test_is_ip_allowed_empty_entries() -> None:
    """Test that empty entries are ignored."""
    allowed = "192.168.1.1,,10.0.0.1"
    assert is_ip_allowed("192.168.1.1", allowed) is True
    assert is_ip_allowed("10.0.0.1", allowed) is True


def test_is_ip_allowed_invalid_client_ip() -> None:
    """Test that invalid client IPs return False."""
    assert is_ip_allowed("not-an-ip", "192.168.1.1") is False
    assert is_ip_allowed("", "192.168.1.1") is False


def test_is_ip_allowed_invalid_whitelist_entry() -> None:
    """Test that invalid whitelist entries are skipped."""
    allowed = "192.168.1.1,invalid,10.0.0.1"
    assert is_ip_allowed("192.168.1.1", allowed) is True
    assert is_ip_allowed("10.0.0.1", allowed) is True
    assert is_ip_allowed("8.8.8.8", allowed) is False


def test_is_ip_allowed_localhost() -> None:
    """Test localhost addresses."""
    allowed = "127.0.0.1"
    assert is_ip_allowed("127.0.0.1", allowed) is True
    assert is_ip_allowed("127.0.0.2", allowed) is False

    allowed_range = "127.0.0.0/8"
    assert is_ip_allowed("127.0.0.1", allowed_range) is True
    assert is_ip_allowed("127.255.255.255", allowed_range) is True
