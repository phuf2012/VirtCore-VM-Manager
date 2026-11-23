# Security policy

VirtCore is beta software and should be used only on systems you administer. It starts a local HTTP interface on `127.0.0.1` by default and invokes libvirt tools as the logged-in user. Do not expose it to a network by changing `VIRTCORE_HOST` unless you have placed appropriate authentication and access controls in front of it; the current interface has no login system.

## Reporting a vulnerability

Please do not publish exploitable details in a public issue. Use GitHub's **Report a vulnerability** action on the repository's Security tab to contact the maintainers privately. Include the affected version, impact, and steps to reproduce when safe to do so.

Security fixes and supported-version information will be added here as the project matures.
