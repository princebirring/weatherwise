"""The one way this project opens web addresses.

Certificates are checked against Mozilla's maintained list (certifi), so a request behaves the
same on a laptop, in the container and on AWS. Some systems' own lists lag behind: macOS's
/etc/ssl/cert.pem lacks Sectigo's 2021 root (R46), which SACHET's certificate chains to, so
official warnings looked "unavailable" there.
"""

import ssl
import urllib.request

import certifi

TLS = ssl.create_default_context(cafile=certifi.where())


def urlopen(request: str | urllib.request.Request, timeout: float):
    return urllib.request.urlopen(request, timeout=timeout, context=TLS)
