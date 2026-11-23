# VirtCore 1.0.0 Beta

**A Linux-first desktop interface for QEMU/KVM virtual machines.** VirtCore helps you create and control Linux VMs from a local web dashboard. The project is in beta; this first release targets Debian and Ubuntu hosts.

> GitHub release title: **VirtCore 1.0.0 Beta**

## What works today

- List VMs registered with the local libvirt system connection.
- Create a VM from a local `.iso` or `.img` installer.
- Choose the VM name, memory, processor count, and virtual disk size.
- Start, pause, resume, shut down, and delete VMs.
- See whether the host can connect to libvirt.

VirtCore currently manages **Linux guests on a Linux QEMU/KVM host**. Windows guests and additional host platforms are planned for later releases.

## Install

Download `virtcore_1.0.0~beta_all.deb` from [Releases](https://github.com/phuf2012/VirtCore-VM-Manager/releases), then install it from the directory containing the file:

```sh
sudo apt install ./virtcore_1.0.0~beta_all.deb
```

Launch **VirtCore 1.0.0 Beta** from your desktop application menu. The package depends on Python 3, QEMU/KVM, libvirt, and `virt-install` and will ask APT to install those packages if needed.

## Host setup

Make sure hardware virtualization is enabled in firmware and that the libvirt service is running. VirtCore uses the `qemu:///system` libvirt connection by default. On Debian or Ubuntu, a typical user setup is:

```sh
sudo usermod -aG libvirt "$USER"
```

Sign out and back in for the group change to take effect. Distribution policy can vary; follow your distribution's libvirt guidance if it differs. VirtCore does not elevate itself and cannot bypass libvirt permissions.

The installer image path must exist on the Linux host running VirtCore. VM disks are created through `virt-install` in the libvirt default storage pool.

## Build from source

Requirements: Python 3, `dpkg-deb`, and the VM dependencies above. From the repository root:

```sh
./build-deb.sh
```

This creates `dist/virtcore_1.0.0~beta_all.deb`. To run without installing the package:

```sh
python3 app.py
```

Open <http://127.0.0.1:8765>. The app binds to localhost by default. You can set `VIRTCORE_PORT` to change the port, `VIRTCORE_LIBVIRT_URI` to choose another libvirt URI, and `VIRTCORE_HOST` to override the bind address.

## Known limitations

- The interface is a local browser-based desktop app, not a standalone hypervisor or guest console.
- Installer images must already be downloaded; ISO discovery and downloads are not included yet.
- Guest installation proceeds in the VM's graphical console, which may be opened through a SPICE client or virt-manager.
- VM configuration editing, snapshots, USB passthrough, and networking controls are not included in this beta.
- The package currently targets Debian/Ubuntu x86-64 hosts.

## Contributing and support

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. For security issues, use the process in [SECURITY.md](SECURITY.md) rather than posting exploit details publicly. General bugs and feature requests belong in [GitHub Issues](https://github.com/phuf2012/VirtCore-VM-Manager/issues).

## License

VirtCore is distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
