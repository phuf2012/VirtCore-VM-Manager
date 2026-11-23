# Contributing

Thanks for helping improve VirtCore. The project is currently focused on Linux hosts using QEMU/KVM and libvirt.

## Before opening a change

- Check the open issues and discussions to avoid duplicate work.
- For a large change, open an issue first to agree on the behavior and scope.
- Keep changes focused and document any new setup steps or host dependencies.
- Do not include VM disk images, ISO files, credentials, or host-specific data.

## Local workflow

1. Create a branch for your change.
2. Make the change and build the Debian package with `./build-deb.sh` when packaging files are affected.
3. Describe the user-visible change and host environment in your pull request.

VirtCore currently has no automated application test suite. Please state which manual checks you performed and their results. Do not include real machine names, storage paths, or other private host details in reports.

## Pull requests

Use a clear title, explain why the change is useful, and include screenshots for visible interface changes. Call out compatibility changes and new dependencies. All contributions are provided under the repository's GPL-3.0 license.
