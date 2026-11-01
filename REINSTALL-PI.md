# Reinstalling cornholio (Raspberry Pi 4, USB-SSD boot)

Fresh install of Raspberry Pi OS Lite 64-bit on the external USB SSD, replacing the old
32-bit Raspbian 10 (buster). Nothing from the old install is kept.

Current state (2026-10-10): Raspberry Pi OS Lite 64-bit based on Debian 13 (trixie), root on
`/dev/sda2` (the SSD), bootloader 2026-09-23, `BOOT_ORDER=0xf41`.

## Hardware

- Raspberry Pi 4 Model B Rev 1.4, 8 GB RAM
- Samsung 970 EVO 500 GB in a JMicron USB 3 enclosure (`152d:0583`). The Pi **boots from this SSD**;
  no SD card is used.
- Ethernet, 192.168.178.27, reserved for the Pi in the FRITZ!Box (always the same IPv4 address)

## SSH access from the Mac

`~/.ssh/config` has a `cornholio` entry (user `pi`). It authenticates with the Secretive key
`cornholio` (Secure Enclave, no Touch ID required) through the default agent; `IdentityFile
~/.ssh/cornholio_secretive.pub` selects that key. The public key comes from
`ssh-add -L | grep cornholio@secretive`.

The Pi accepts only this key. The older RSA key `~/.ssh/id_rsa_cornholio` (passphrase in the
Keychain) was removed from `authorized_keys` and deleted from the Mac (2026-10-10): it failed in
BatchMode whenever the Keychain couldn't hand out the passphrase. If the Secretive key is ever lost, log in at the Pi's console and add a new
public key, or reinstall (below).

## Steps

1. **Shut down the Pi**: `ssh cornholio sudo poweroff`. Wait for the green LED to stop blinking, then
   unplug power and the SSD.
2. **Connect the SSD to the Mac** using the same USB enclosure.
3. **Open Raspberry Pi Imager**. Install it with `brew install --cask raspberry-pi-imager` if needed.
   - Device: **Raspberry Pi 4**
   - OS: Raspberry Pi OS (other) → **Raspberry Pi OS Lite (64-bit)**
   - Storage: the **Samsung 970 EVO (~500 GB)**. Check the size so you don't pick the wrong disk.
4. **OS customisation** ("Edit settings"):
   - Hostname: `cornholio`
   - Username `pi` and a password (needed for `sudo`)
   - Wi-Fi: leave off
   - Locale: Europe/Berlin, keyboard layout as preferred
   - Services: **Enable SSH → Allow public-key authentication only**, and paste the contents of
     `~/.ssh/cornholio_secretive.pub` (`pbcopy < ~/.ssh/cornholio_secretive.pub`)
5. **Write** the image. This erases the whole SSD.
6. **Put the SSD back on the Pi** (preferably a blue USB 3 port) and power on. The first boot expands
   the filesystem and reboots once, which takes 1–2 minutes.

## After the first boot

- Remove the old host key: `ssh-keygen -R 192.168.178.27` (the reinstalled Pi has a new SSH host key).
- The FRITZ!Box reserves 192.168.178.27 for the Pi's network card, so the IP should stay the same.
  If not, try `ssh pi@cornholio.fritz.box` or check the FRITZ!Box device list, then update `HostName`
  in `~/.ssh/config`. While the Pi is down, the LAN has no DNS (Pi-hole); devices fall back only once
  you set the FRITZ!Box's "Local DNS server" back to empty.
- Passwordless sudo for `pi` (Claude Code runs sudo non-interactively):
  `echo 'pi ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/010_pi-nopasswd && sudo chmod 440 /etc/sudoers.d/010_pi-nopasswd && sudo visudo -c`
- Update the system: `sudo apt update && sudo apt full-upgrade -y`, then reboot.
- Update the bootloader EEPROM: `sudo rpi-eeprom-update -a`, then reboot.
- Check the boot order: `rpi-eeprom-config | grep BOOT_ORDER`. `0xf41` (SD, then USB) works without
  an SD card; `0xf14` tries USB first.
- Set up the monitoring stack: run `/setup` in Claude Code (README path 2A: the Pi boots from the SSD,
  so Docker's default data-root is already on the SSD).
- Restore data and backups: README → Backups → "After a full reinstall" (restic password from the
  password manager, new SSH key for the Synology, restore volumes and env files, reinstall the
  `cornholio-backup` timer).

## If the Pi doesn't boot after the bootloader (EEPROM) update

Happened on 2026-10-10 after updating the bootloader from 2022-02-08 to 2026-09-23: the Pi didn't
come back on the network. **A power cycle (step 1) fixed it**: the update had been applied
(bootloader 2026-09-23, VL805 USB firmware 000138c0) and it booted normally from the SSD afterwards.

1. Unplug the power for 10 s and power on again (SSD on a blue USB 3 port). Wait 2 min.
2. Still down: connect HDMI (port next to USB-C). The bootloader diagnostic screen shows its version,
   boot mode and the error. Alternatively count the green LED's long/short flash pattern.
3. Recovery: on the other Mac, Raspberry Pi Imager → Misc utility images → Bootloader (Pi 4 family)
   → **USB Boot**, write it to a microSD card. Boot the Pi from that card **without the SSD**; when
   the green LED blinks steadily / the screen turns green, the EEPROM has been rewritten. Remove the
   card, reconnect the SSD, power on. The OS on the SSD isn't touched.
