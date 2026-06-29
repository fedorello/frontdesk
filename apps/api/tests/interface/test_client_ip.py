"""client_ip reads the real client behind a trusted proxy and resists X-Forwarded-For spoofing."""

from starlette.requests import Request
from starlette.types import Scope

from frontdesk.interface.client_ip import client_ip


def _request(forwarded_for: str | None, peer: str | None = "10.0.0.1") -> Request:
    headers = [(b"x-forwarded-for", forwarded_for.encode())] if forwarded_for is not None else []
    scope: Scope = {
        "type": "http",
        "headers": headers,
        "client": (peer, 0) if peer is not None else None,
    }
    return Request(scope)


def test_takes_the_hop_the_trusted_proxy_recorded() -> None:
    # Client prepends fakes; the trusted proxy appends the real IP (right-most). hops=1 -> real.
    assert client_ip(_request("1.1.1.1, 2.2.2.2, 9.9.9.9"), trusted_proxy_hops=1) == "9.9.9.9"


def test_spoofing_the_prefix_does_not_change_the_result() -> None:
    one = client_ip(_request("evil, 9.9.9.9"), trusted_proxy_hops=1)
    two = client_ip(_request("a, b, c, 9.9.9.9"), trusted_proxy_hops=1)
    assert one == two == "9.9.9.9"  # the attacker-controlled prefix is ignored


def test_two_trusted_hops_take_the_second_from_the_right() -> None:
    assert client_ip(_request("client, 8.8.8.8, edge"), trusted_proxy_hops=2) == "8.8.8.8"


def test_falls_back_to_the_socket_peer_when_chain_is_short() -> None:
    assert client_ip(_request(None, peer="10.0.0.5")) == "10.0.0.5"  # no forwarded header
    short = _request("only-one", peer="10.0.0.5")
    assert client_ip(short, trusted_proxy_hops=2) == "10.0.0.5"  # chain shorter than the hop count


def test_unknown_when_there_is_neither_header_nor_peer() -> None:
    assert client_ip(_request(None, peer=None)) == "unknown"
