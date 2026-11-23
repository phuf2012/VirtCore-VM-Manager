# VirtCore 1.0.0 Beta 2

**A Linux-first desktop interface for QEMU/KVM virtual machines.** VirtCore helps you create and control Linux VMs from a local desktop window. This beta targets Debian and Ubuntu hosts.

> GitHub release title: **VirtCore 1.0.0 Beta 2**

## What works today

- List machines registered with the libvirt system connection.
- Create a VM from a local `.iso` or `.img` installer using a native file picker.
- Set the VM name, memory, processor count, and virtual disk size.
- Start, pause, resume, gracefully shut down, or delete a VM.
- Open the VM's local SPICE console with `virt-viewer`.
- See libvirt connection state and operation errors in the app.

VirtCore currently manages **Linux guests on a Linux QEMU/KVM host**. Windows guests and additional host platforms are planned for later releases.

## Install

Download `virtcore_1.0.0~beta2_all.deb` from [Releases](https://github.com/phuf2012/VirtCore-VM-Manager/releases), then install it from the directory containing the file:

```sh
sudo apt install ./virtcore_1.0.0~beta2_all.deb
```

Launch **VirtCore 1.0.0 Beta 2** from your desktop application menu. The package depends on Python 3, Tk, QEMU/KVM, libvirt, `virt-install`, and `virt-viewer`; APT installs these packages if needed.

## Host setup

Make sure hardware virtualization is enabled in firmware and that the libvirt service is running. VirtCore uses `qemu:///system` by default. On Debian or Ubuntu, a typical user setup is:

```sh
sudo usermod -aG libvirt "$USER"
```

Sign out and back in for the group change to take effect. Distribution policy varies, so follow your distribution's libvirt guidance if it differs. VirtCore runs commands as the logged-in user and does not elevate itself.

VM disks are created through `virt-install` in the libvirt default storage pool. The installer image is selected from a file on the same Linux host.

## Build from source

Requirements: Python 3 with Tk, `dpkg-deb`, and the VM dependencies above. From the repository root:

```sh
./build-deb.sh
```

This creates `dist/virtcore_1.0.0~beta2_all.deb`. To run directly from source:

```sh
python3 app.py
```

Set `VIRTCORE_LIBVIRT_URI` to manage another libvirt connection.

## Known limitations

- VirtCore manages VMs; it is not a hypervisor itself.
- Installer images must already be downloaded; image discovery and downloads are not included.
- VM configuration editing, snapshots, USB passthrough, and network controls are not included in this beta.
- The Debian package currently targets Debian/Ubuntu x86-64 hosts.

## Contributing and support

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. For security issues, use the process in [SECURITY.md](SECURITY.md) rather than posting exploit details publicly. General bugs and feature requests belong in [GitHub Issues](https://github.com/phuf2012/VirtCore-VM-Manager/issues).

## License

VirtCore is distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
