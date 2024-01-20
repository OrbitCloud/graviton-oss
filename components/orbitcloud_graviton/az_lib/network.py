import ipaddress


def is_public_ip(ip):
    """Check if an IP address or network is public."""
    private_networks = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        # Add other reserved ranges as needed.
    ]
    try:
        ip_net = ipaddress.ip_network(ip, strict=False)
        return not any(ip_net.overlaps(private_net) for private_net in private_networks)
    except ValueError as e:
        # Handle the error or re-raise with a clearer message
        raise ValueError(f"Invalid IP address format: {ip}") from e
