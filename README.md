# Bluetooth Tweaker Pro (Community Edition & Reverse Engineering Guide)

> [!TIP]
> **Quick Start for End Users:**  
> If you simply want to run and use the custom **Bluetooth Tweaker GUI** to inspect audio codecs, fix volume synchronization bugs, or manage microphone muting without licensing restrictions, follow the **[Quick Start: How to Use the GUI](#quick-start-how-to-use-the-gui)** section below and **skip the rest of this document**.
> 
> If you are a developer, driver engineer, or security researcher interested in how Bluetooth Tweaker operates under the hood, how kernel filter drivers hook AVDTP audio negotiation, or how hexadecimal codec bitmasks are parsed, the second part of this document (**[Reverse Engineering Findings & Deep Dive](#reverse-engineering-findings--deep-dive)**) contains our complete technical analysis for study purposes.

---

## Quick Start: How to Use the GUI

### 1. Prerequisites
- **Operating System:** Windows 10 or Windows 11 (64-bit).
- **Python:** Python 3.8+ installed (tested with Python 3.10 – 3.14).
- **Underlying Driver:** Official Bluetooth Tweaker installed (from `www.bluetoothgoodies.com`).  
  *Why:* This installs the kernel filter driver `BtTweakerFltr.sys`. You do **not** need to purchase an official license or run the official `BtTweakerUI.exe`; our community GUI talks directly to the driver and driver traces.

### 2. Installation
Open PowerShell in this project folder and install PyQt5:
```powershell
pip install PyQt5
```

### 3. Launching the GUI
Run PowerShell or Command Prompt as **Administrator** (required to write hardware parameters to `HKLM:\SYSTEM\CurrentControlSet\Services\BtTweakerFltr\Parameters\UserParams`):
```powershell
python app.py
```

### 4. Key Features & Controls
- **Real-Time Codec Discovery:** Completely dynamic detection of supported codecs (SBC bitpool ranges, MPEG-2/4 AAC profiles, Sony LDAC, Qualcomm aptX/aptX-HD/FastStream) sniffed from kernel traces and Windows CoreAudio endpoints. Zero hardcoded device profiles.
- **Refresh CODEC Information:** Click to re-scan Bluetooth connection events and refresh capability lists without restarting the application.
- **Disable Hardware Volume Control:** Check this option to force Windows software volume scaling. This permanently fixes issues where headset volume jumps uncontrollably or stays stuck at 100%.
- **Mute Microphone:** Mutes headset microphone streams at the kernel driver filter level on HFP/HSP hands-free profiles.
- **Multi-Language Interface:** Seamlessly switch between **English**, **Tiếng Việt**, **简体中文**, and **日本語** with immediate persistence to `config.json`.

### 5. Troubleshooting

#### Codec info missing for a newly-paired device

> [!IMPORTANT]
> The kernel filter driver `BtTweakerFltr.sys` is registered **per device instance** (not globally). Normally `BtTweakerSvc.exe` writes this entry automatically when a new device is paired. If that service is stopped, expired, or otherwise unavailable, a brand-new device may not get the filter attached — so the GUI cannot sniff its AVDTP codec frames.

**How we handle this automatically:**  
Our GUI calls `ensure_filter_attached(mac)` (see [`core/device_manager.py`](core/device_manager.py)) whenever it detects a device with no codec information. This function:
1. Walks all relevant BTHENUM PnP device instances under `HKLM\SYSTEM\CurrentControlSet\Enum\BTHENUM\` that match the device's MAC address.
2. Checks whether `BtTweakerFltr` is present in each instance's `LowerFilters` (`REG_MULTI_SZ`) value.
3. If missing, writes the entry (requires the app to be running as **Administrator**).
4. Returns a message instructing the user to **disconnect and reconnect** the device so Windows re-loads the driver stack with the filter now attached.

**Manual fix (PowerShell, if needed):**
```powershell
# Replace the instance path with the actual one from your system
$inst = "HKLM:\SYSTEM\CurrentControlSet\Enum\BTHENUM\{0000110b-0000-1000-8000-00805f9b34fb}_VID&...\_YourMAC_C00000000"
$existing = (Get-ItemProperty $inst -Name LowerFilters -EA SilentlyContinue).LowerFilters
if ("BtTweakerFltr" -notin $existing) {
    Set-ItemProperty $inst -Name LowerFilters -Value (@($existing) + "BtTweakerFltr") -Type MultiString
    Write-Host "Done — disconnect and reconnect the device."
}
```

| Scenario | Effect | Resolution |
|----------|--------|------------|
| Device previously paired, service stopped | ✅ Filter already in registry — works fine | None needed |
| **New device paired, service dead** | ⚠️ Filter entry missing — no codec sniff | GUI auto-fixes via `ensure_filter_attached()` |
| `BtTweakerFltr.sys` driver uninstalled | ❌ Driver not loaded at all | Re-install Bluetooth Tweaker |
| App not running as Administrator | ❌ Cannot write to `HKLM\Enum` | Re-launch as Administrator |

---

## Reverse Engineering Findings & Deep Dive

**Date:** September 20, 2026  
**Target:** Bluetooth Tweaker v1.4.9 (Win32 Service & Kernel Filter Driver)  
**Vendor:** Luculent Systems, LLC (`www.bluetoothgoodies.com`)  
**Install Path:** `C:\Program Files\Luculent Systems\Bluetooth Tweaker`  

---

## Key Insight & Summary

**Bluetooth Tweaker** is an advanced Bluetooth audio diagnostic and parameter control suite for Windows. Unlike Alternative A2DP Driver (which replaces the standard Windows A2DP audio driver to encode audio), **Bluetooth Tweaker operates as a Kernel Mode Filter Driver (`BtTweakerFltr.sys`) attached to the standard Windows Bluetooth stack (`BTHENUM` and `BTH\MS_BTHBRB`)**.

This filter driver sniffs low-level AVDTP and SDP protocol packets (which normal Windows APIs hide), allowing Bluetooth Tweaker to:
1. Decode supported A2DP codecs (SBC bitpool ranges, AAC sub-profiles, aptX, aptX HD, LDAC bitrates, FastStream, vendor codecs).
2. Override hardware volume control (`DisableHardwareVolume`) to fix headphones where Windows volume sync fails.
3. Manage microphone muting (`MicMute`) and AVRCP proxy media transport control (`BtTweakerProxy.exe`).
4. Read battery levels via GATT Battery Service (`0x180F`) and vendor-specific Bluetooth LE commands.

**The core architectural finding:** All device settings and filter behaviors are controlled via standard Windows Registry keys under `HKLM:\SYSTEM\CurrentControlSet\Services\BtTweakerFltr\Parameters\UserParams`. Writing DWORD values to these registry keys immediately changes driver and service behavior.

---

## Table of Contents

- **[Quick Start: How to Use the GUI](#quick-start-how-to-use-the-gui)** *(For End Users)*
- **[Reverse Engineering Analysis](#reverse-engineering-findings--deep-dive)** *(For Developers & Researchers)*
  1. [Architecture Overview](#1-architecture-overview)
  2. [Component Breakdown](#2-component-breakdown)
  3. [Kernel Driver & Service Deep Dive](#3-kernel-driver--service-deep-dive)
  4. [Registry Schema (Complete)](#4-registry-schema-complete)
  5. [Feature & Parameter Reference (AVDTP Hex Analysis)](#5-feature--parameter-reference)
  6. [Licensing & Activation System](#6-licensing--activation-system)
  7. [Building a Custom GUI / Alternative UI](#7-building-a-custom-gui--alternative-ui)
  8. [Useful PowerShell Commands](#8-useful-powershell-commands)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│  BtTweakerUI.exe  (Qt5 Widgets Desktop GUI)              │
│  - Displays device status, battery %, codecs, settings    │
│  - Validates RSA-signed license files                     │
│  - Writes configuration to UserParams Registry keys       │
└────────────────────────┬─────────────────────────────────┘
                         │ Registry writes
┌────────────────────────┴─────────────────────────────────┐
│  BtTweakerSvc.exe  (Win32 Service - "BtTweakerSvc")        │
│  - Runs as NT AUTHORITY\SYSTEM                            │
│  - PnP notification watcher (CM_Register_Notification)    │
│  - Watched registry key watcher (RegNotifyChangeKeyValue) │
│  - Manages BtTweakerFltr.sys driver filter attachments   │
│  - Syncs UserParams between HKLM\SYSTEM and HKLM\SOFTWARE│
└────────────────────────┬─────────────────────────────────┘
                         │ 
┌────────────────────────┼─────────────────────────────────┐
│  BtTweakerProxy.exe    │  (WinRT Helper Utility)          │
│  - Windows Media Transport Controls (SystemMediaControls)│
│  - Audio Device Monitor & GATT Battery Service reader     │
└────────────────────────┬─────────────────────────────────┘
                         │ Registry reads / Filter hooks
┌────────────────────────┴─────────────────────────────────┐
│  BtTweakerFltr.sys  (KMDF Kernel Lower Filter Driver)    │
│  - Attached to BTHENUM A2DP/AVRCP nodes & BTH\MS_BTHBRB   │
│  - Sniffs low-level AVDTP/SDP codec capability frames    │
│  - Intercepts hardware volume & microphone mute IOCTLs   │
│  - Reads device options from UserParams registry keys    │
└────────────────────────┬─────────────────────────────────┘
                         │ Bluetooth L2CAP / SDP / HCI
                         ▼
             Bluetooth Headphones & Speakers
```

---

## 2. Component Breakdown

### Installed Executables & Drivers

| File | Size | Type | Purpose |
|------|------|------|---------|
| `BtTweakerUI.exe` | 1,159 KB | Qt5 Desktop Application | Main User Interface & license management |
| `BtTweakerSvc.exe` | 1,136 KB | Win32 Background Service | PnP device watcher, registry sync, filter installer |
| `BtTweakerProxy.exe` | 1,392 KB | WinRT / Win32 Helper | System Media Controls & GATT battery status listener |
| `Drivers\BtTweakerFltr.sys` | 57 KB | KMDF Kernel Filter Driver | Low-level Bluetooth AVDTP/SDP sniffer & control filter |
| `libcrypto-1_1-x64.dll` | 3,439 KB | OpenSSL Crypto Library | Cryptographic operations |
| `libssl-1_1-x64.dll` | 695 KB | OpenSSL SSL Library | Network / license communication |
| `Qt5Core.dll` / `Qt5Gui.dll` | ~13 MB | Qt 5.15 Framework | GUI runtime libraries |

### PE Header & Build Metadata

- **Architecture:** `x86_64` (AMD64)
- **Subsystem:** Win32 GUI (`0x2`) for UI/Proxy, Win32 Console/Service (`0x3`) for Svc, Native Kernel (`0x1`) for Driver.
- **Compiler:** Microsoft Visual C++ 2019 / 2022 (MSVC 14.x)
- **Internal PDB Paths:**
  - UI: `C:\Products\BT\BT-1.4.9-d\Build\x64\RelWithDebInfo\BtTweakerUI.pdb`
  - Service: `C:\Products\BT\BT-1.4.9-d\Build\x64\RelWithDebInfo\BtTweakerSvc.pdb`
  - Proxy: `C:\Products\BT\BT-1.4.9-d\Build\x64\RelWithDebInfo\BtTweakerProxy.pdb`
  - Driver: `C:\Products\BT\BT-1.4.9-d\DRV\Build\x64\Release\BtTweakerFltr.pdb`

---

## 3. Kernel Driver & Service Deep Dive

### KMDF Filter Driver (`BtTweakerFltr.sys`)

- **Driver Class:** Bluetooth Devices (`{e0cbf06c-cd8b-4647-bb8a-263b43f0f974}`)
- **Target Attachments (`LowerFilters`):**
  - `BTHENUM\{0000110b-0000-1000-8000-00805f9b34fb}` (A2DP Audio Sink)
  - `BTHENUM\{0000110c-0000-1000-8000-00805f9b34fb}` (AVRCP Target)
  - `BTHENUM\{0000110e-0000-1000-8000-00805f9b34fb}` (AVRCP Controller)
  - `BTH\MS_BTHBRB` (Bluetooth Request Block driver)

When a Bluetooth audio device connects, `BtTweakerFltr.sys` intercepts raw Bluetooth Request Blocks (BRBs) and L2CAP SDP/AVDTP packets. It decodes:
- **SBC:** Min/Max Bitpool (e.g. 2-53), Sample Frequencies (44.1kHz / 48kHz), Channel Modes (Mono, Dual Channel, Stereo, Joint Stereo).
- **AAC:** Object Types (MPEG-2 AAC LC, MPEG-4 AAC LC, LTP, SC, HE-AAC, HE-AACv2, ELDv2), Bitrate, Sample Rates.
- **aptX & aptX HD:** Vendor ID `0x0000000A` (CSR / Qualcomm), Codec ID `0x0001` (aptX) / `0x0024` (aptX HD).
- **LDAC:** Vendor ID `0x0000012D` (Sony), Codec ID `0x00AA`.

### Windows Service (`BtTweakerSvc.exe`)

- **Service Name:** `BtTweakerSvc`
- **Display Name:** `Bluetooth Tweaker Service`
- **Execution Level:** `NT AUTHORITY\SYSTEM`
- **Responsibilities:**
  1. Monitors Bluetooth device connection events using `CM_Register_Notification`.
  2. Ensures `BtTweakerFltr.sys` is listed under `LowerFilters` for relevant PnP Bluetooth device instances.
  3. Uses `RegNotifyChangeKeyValue` to monitor `HKLM:\SYSTEM\CurrentControlSet\Services\BtTweakerFltr\Parameters\UserParams` for GUI configuration changes.
  4. Manages system & per-device trial status (`TrialSystem` and `TrialCODEC` license records).

---

## 4. Registry Schema (Complete)

All user configurations, device overrides, and trial states are stored under two primary registry paths:
1. Driver Parameter Storage: `HKLM\SYSTEM\CurrentControlSet\Services\BtTweakerFltr\Parameters\UserParams`
2. Software Mirror Storage: `HKLM\SOFTWARE\Luculent Systems\Bluetooth Tweaker\UserParams`

### Key Hierarchy & Value Definitions

```text
HKLM\SYSTEM\CurrentControlSet\Services\BtTweakerFltr\Parameters\UserParams\
├── CodecInfo\
│   └── {mac_address}\
│       ├── Next     (DWORD) : Desired Codec index/mode (1 = Default/Active)
│       ├── Current  (DWORD) : Currently active Codec index
│       └── Updated  (QWORD) : Windows FILETIME timestamp of last change
├── DisableHardwareVolume\
│   └── {mac_address}\
│       ├── Next     (DWORD) : 0 = Enable HW Volume, 1 = Disable HW Volume
│       └── Updated  (QWORD) : FILETIME timestamp
├── MicMute\
│   └── {mac_address}\
│       └── Current  (DWORD) : 0 = Unmuted, 1 = Muted
├── AvrcpProxy\
│   └── {mac_address}\
│       └── Next     (DWORD) : AVRCP Proxy routing state
├── A2dpSink\
│   └── {mac_address}\
│       └── Data     (REG_BINARY) : Captured raw A2DP SDP/AVDTP capability payload
└── License\
    ├── TrialSystem (REG_BINARY) : Base64/ASCII key-value string for system trial
    ├── PaidSystem  (REG_BINARY) : Retail system license string
    └── {mac_address}\
        ├── TrialCODEC (REG_BINARY) : Per-device trial license payload
        └── PaidCODEC  (REG_BINARY) : Per-device retail license payload
```

*Note: `{mac_address}` is formatted as a 12-character lowercase hex string without colons or dashes (e.g., `b4e7b3b6ebe8`).*

---

## 5. Feature & Parameter Reference

### 1. Hardware Volume Control (`DisableHardwareVolume`)
- **Problem:** Many Bluetooth headphones have broken hardware volume synchronization on Windows 10/11, causing volume steps to jump uncontrollably or stay locked at 100%.
- **Solution:** Setting `DisableHardwareVolume\{mac}\Next = 1` forces Windows to perform software PCM volume scaling before sending audio to the headset, bypassing the headset's physical volume amplifier control.

### 2. Microphone Muting (`MicMute`)
- **Problem:** Muting the headset microphone on Bluetooth HFP/HSP profiles often fails or produces audible clicks/beeps.
- **Solution:** Setting `MicMute\{mac}\Current = 1` causes `BtTweakerFltr.sys` to drop or zero-out incoming audio streams from the headset's SCO/eSCO microphone channel at the driver level.

### 3. Codec Capability Inspection (AVDTP Sniffing, Trace Decoding & Hex Analysis)

#### A. Architecture of Codec Discovery

Standard Windows Bluetooth APIs do **not** expose Bluetooth AVDTP (Audio/Video Distribution Transport Protocol) codec negotiation frames to user-mode applications. Windows terminates the Bluetooth audio profile inside the kernel (`BthA2dp.sys`, `bthport.sys`) and only presents opaque multimedia render endpoints (`MMDevices`) to user-mode CoreAudio / WASAPI.

##### How Bluetooth A2DP Codec Negotiation Works (Bluetooth SIG Standard)
When a Bluetooth audio headset connects to a PC, the following protocol sequence occurs over L2CAP Protocol/Service Multiplexer (PSM) `0x0019` (AVDTP Signaling Channel):
1. **L2CAP Connection Establishment:** An ACL data link is opened between PC (Source) and Headset (Sink) over PSM `0x0019`.
2. **`AVDTP_DISCOVER` (Signal ID `0x01`):** The PC sends a discovery command. The headset responds with a list of all its available **Stream Endpoints (SEPs)**, each identified by a Stream Endpoint Identifier (**SEID**), Media Type (`0x00` = Audio), and Endpoint Role (`0x00` = Sink).
3. **`AVDTP_GET_CAPABILITIES` (Signal ID `0x02`) or `AVDTP_GET_ALL_CAPABILITIES` (Signal ID `0x0C`):** The PC iterates through each advertised SEID requesting its Service Capabilities. The headset returns capability blocks:
   - **Service Category `0x01`:** Media Transport
   - **Service Category `0x02`:** Reporting
   - **Service Category `0x07`:** **Media Codec** (The core payload containing codec type, sample rates, channel modes, bitrates)
   - **Service Category `0x08`:** Content Protection (SCMS-T / DTCP)
   - **Service Category `0x0A`:** Delay Reporting
4. **`AVDTP_SET_CONFIGURATION` (Signal ID `0x03`):** The PC selects one specific SEID and sends back the negotiated parameters (e.g., 44.1 kHz, Joint Stereo, Bitpool 38 for SBC; or 48 kHz Stereo for AAC).
5. **`AVDTP_OPEN` (Signal ID `0x06`) & `AVDTP_START` (Signal ID `0x07`):** The streaming channel is opened and audio data begins flowing over RTP/AVDTP Media packets.

##### How Bluetooth Tweaker Captures This Data
Bluetooth Tweaker installs **`BtTweakerFltr.sys`** as a Kernel-Mode Lower Filter Driver attached to:
- `BTHENUM\{0000110b-0000-1000-8000-00805f9b34fb}` (A2DP Audio Sink)
- `BTH\MS_BTHBRB` (Bluetooth Request Block driver)

The filter driver hooks `IRP_MJ_INTERNAL_DEVICE_CONTROL` requests carrying Bluetooth Request Blocks (**BRBs**), specifically `BRB_L2CA_ACL_TRANSFER`. It inspects the incoming and outgoing L2CAP payload buffers on PSM `0x0019`. When it detects AVDTP Service Category `0x07` frames, it clones the capability payload and emits it through Event Tracing for Windows (ETW).

---

#### B. Event Tracing for Windows (ETW) Subsystem

The filter driver emits sniffed Bluetooth packets and driver telemetry via ETW:
- **ETW Provider GUID:** `{045f889e-3afe-4a8c-be2d-85241829b6e9}`
- **Log Files on Disk:**
  - `C:\ProgramData\Luculent Systems\AltA2DP\Trace\AltA2DP.etl`
  - `C:\ProgramData\Luculent Systems\Bluetooth Tweaker\Trace\BtTweaker.etl`

##### Real-Time UI Subscription (`BtTweakerUI.exe`)
In `BtTweakerUI.exe` (disassembled at RVA `0x1d1c0` - `0x1d2f0`), the UI connects directly to this ETW stream:
```c
// 1. Start a real-time ETW session
EVENT_TRACE_PROPERTIES props;
ZeroMemory(&props, sizeof(props));
props.Wnode.BufferSize = sizeof(props) + 1024;
props.Wnode.Flags = WNODE_FLAG_TRACED_GUID;
props.LogFileMode = EVENT_TRACE_REAL_TIME_MODE; // 0x00000100
StartTraceW(&hSession, L"Bluetooth Tweaker UI Session <PID>", &props);

// 2. Enable the BtTweakerFltr ETW Provider
EnableTrace(TRUE, 0, TRACE_LEVEL_INFORMATION, &BtTweakerProviderGuid, hSession);

// 3. Open real-time trace consumer
EVENT_TRACE_LOGFILEW logfile;
logfile.LoggerName = L"Bluetooth Tweaker UI Session <PID>";
logfile.ProcessTraceMode = PROCESS_TRACE_MODE_REAL_TIME | PROCESS_TRACE_MODE_EVENT_RECORD; // 0x10000100
logfile.EventRecordCallback = &OnEtwEventRecord;
TRACEHANDLE hTrace = OpenTraceW(&logfile);

// 4. Process live events on a background worker thread
ProcessTrace(&hTrace, 1, NULL, NULL);
```

---

#### C. AVDTP Service Category 0x07 (Media Codec) Structure

In the Bluetooth AVDTP specification, every Stream Endpoint (SEP) advertises its capabilities through Service Capabilities. Category `0x07` defines the **Media Codec**:

| Byte Offset | Field Name | Description | Example (SBC) | Example (AAC) | Example (LDAC) |
|-------------|------------|-------------|---------------|---------------|----------------|
| **Byte 0** | Service Category | `0x07` = Media Codec | `0x07` | `0x07` | `0x07` |
| **Byte 1** | LOSC | Length of Service Capabilities | `0x06` (6 bytes) | `0x08` (8 bytes) | `0x0A` (10 bytes) |
| **Byte 2** | Media Type | `0x00` = Audio | `0x00` | `0x00` | `0x00` |
| **Byte 3** | Codec Type | Codec Identifier | `0x00` (SBC) | `0x02` (AAC) | `0xFF` (Vendor) |
| **Byte 4+** | Codec Elements | Codec-specific capability parameters | *(See breakdown below)* | *(See breakdown below)* | *(See breakdown below)* |

---

#### D. Hexadecimal Breakdown by Codec (Bit-by-Bit Reference)

##### 1. SBC (Subband Codec) — Codec Type `0x00` (LOSC = `0x06`)

Payload Layout (4 parameter bytes following the 4-byte header):

```text
Byte 0: [0x07] Service Category (Media Codec)
Byte 1: [0x06] Length of Payload (6 bytes)
Byte 2: [0x00] Media Type (Audio)
Byte 3: [0x00] Codec Type (SBC)
Byte 4: [Octet 0] Sampling Frequency (Bits 7-4) & Channel Mode (Bits 3-0)
Byte 5: [Octet 1] Block Length (Bits 7-4), Subbands (Bits 3-2), Allocation Method (Bits 1-0)
Byte 6: [Min Bitpool] Minimum Bitpool Value
Byte 7: [Max Bitpool] Maximum Bitpool Value
```

###### Octet 0 (Byte 4) Bitmask Details:
| Bit | Hex Value | Meaning |
|-----|-----------|---------|
| `Bit 7` | `0x80` | 16 kHz sampling frequency supported |
| `Bit 6` | `0x40` | 32 kHz sampling frequency supported |
| `Bit 5` | `0x20` | 44.1 kHz sampling frequency supported |
| `Bit 4` | `0x10` | 48 kHz sampling frequency supported |
| `Bit 3` | `0x08` | Mono channel mode supported |
| `Bit 2` | `0x04` | Dual Channel mode supported |
| `Bit 1` | `0x02` | Stereo mode supported |
| `Bit 0` | `0x01` | Joint Stereo mode supported |

###### Octet 1 (Byte 5) Bitmask Details:
| Bit | Hex Value | Meaning |
|-----|-----------|---------|
| `Bit 7` | `0x80` | Block Length 16 supported |
| `Bit 6` | `0x40` | Block Length 12 supported |
| `Bit 5` | `0x20` | Block Length 8 supported |
| `Bit 4` | `0x10` | Block Length 4 supported |
| `Bit 3` | `0x08` | 8 Subbands supported |
| `Bit 2` | `0x04` | 4 Subbands supported |
| `Bit 1` | `0x02` | SNR allocation method supported |
| `Bit 0` | `0x01` | Loudness allocation method supported |

###### Bytes 6 & 7 (Bitpool Range):
- `Byte 6`: Minimum Bitpool value (unsigned 8-bit integer, standard is `0x02` = 2).
- `Byte 7`: Maximum Bitpool value (unsigned 8-bit integer, e.g., `0x26` = 38, `0x35` = 53).

###### Real Trace Comparison (Edifier X2 Plus & UGREEN HiTune Max5c):
- **Supported Capabilities Frame:** `07 06 00 00 FF FF 02 26`
  - `07`: Category 0x07 (Media Codec)
  - `06`: 6 bytes of payload follow
  - `00`: Media Type Audio
  - `00`: Codec Type SBC
  - `FF`: Octet 0 = `1111 1111` in binary -> Supports 16, 32, 44.1, 48 kHz AND Mono, Dual, Stereo, Joint Stereo
  - `FF`: Octet 1 = `1111 1111` in binary -> Supports Block 4, 8, 12, 16; Subbands 4, 8; Alloc SNR, Loudness
  - `02`: Minimum Bitpool = 2
  - `26`: Maximum Bitpool = 38
  - **Decoded String:** `CODEC Type: SBC, Sampling Frequency: 16/32/44.1/48kHz, Channel Mode: Mono/Dual Channel/Stereo/Joint Stereo, Block Length: 4/8/12/16, Subbands: 4/8, Allocation Method: SNR/Loudness, Min/Max Bitpool: 2/38`
- **Active Negotiated Frame:** `07 06 00 00 21 81 02 26`
  - `21`: `0010 0001` -> Bit 5 = 1 (44.1 kHz selected), Bit 0 = 1 (Joint Stereo selected)
  - `81`: `1000 0001` -> Bit 7 = 1 (Block Length 16 selected), Bits 3-2 = `00` (8 Subbands selected), Bit 0 = 1 (Loudness selected)
  - `02`: Min Bitpool = 2
  - `26`: Max Bitpool = 38
  - **Decoded String:** `CODEC Type: SBC, Sampling Frequency: 44.1kHz, Channel Mode: Joint Stereo, Block Length: 16, Subbands: 8, Allocation Method: Loudness, Min/Max Bitpool: 2/38`

---

##### 2. MPEG-2, 4 AAC — Codec Type `0x02` (LOSC = `0x08`)

Payload Layout (6 parameter bytes following the 4-byte header):

```text
Byte 0: [0x07] Service Category (Media Codec)
Byte 1: [0x08] Length of Payload (8 bytes)
Byte 2: [0x00] Media Type (Audio)
Byte 3: [0x02] Codec Type (MPEG-2/4 AAC)
Byte 4: [Object Type]
Byte 5: [Sampling Frequency High] (8 kHz to 44.1 kHz)
Byte 6: [Sampling Frequency Low & Channels] (48 kHz to 96 kHz, Channels 1 & 2)
Byte 7: [VBR Bit (0x80) & Bitrate High 7 bits]
Byte 8: [Bitrate Mid 8 bits]
Byte 9: [Bitrate Low 8 bits]
```

###### Byte 4 (Object Types):
| Bit | Hex Value | Meaning |
|-----|-----------|---------|
| `Bit 7` | `0x80` | MPEG-2 AAC LC (Low Complexity) |
| `Bit 6` | `0x40` | MPEG-4 AAC LC (Low Complexity) |
| `Bit 5` | `0x20` | MPEG-4 AAC LTP (Long Term Prediction) |
| `Bit 4` | `0x10` | MPEG-4 AAC Scalable |

###### Bytes 5 & 6 (Sampling Frequencies & Channels):
- **Byte 5 (Frequencies 8 kHz to 44.1 kHz):**
  - `Bit 7 (0x80)`: 8000 Hz
  - `Bit 6 (0x40)`: 11025 Hz
  - `Bit 5 (0x20)`: 12000 Hz
  - `Bit 4 (0x10)`: 16000 Hz
  - `Bit 3 (0x08)`: 22050 Hz
  - `Bit 2 (0x04)`: 24000 Hz
  - `Bit 1 (0x02)`: 32000 Hz
  - `Bit 0 (0x01)`: 44100 Hz
- **Byte 6 (Frequencies 48 kHz to 96 kHz & Channels):**
  - `Bit 7 (0x80)`: 48000 Hz
  - `Bit 6 (0x40)`: 64000 Hz
  - `Bit 5 (0x20)`: 88200 Hz
  - `Bit 4 (0x10)`: 96000 Hz
  - `Bit 3 (0x08)`: 1 Channel (Mono) supported
  - `Bit 2 (0x04)`: 2 Channels (Stereo) supported
  - `Bits 1-0`: Reserved for future addition (RFA = 0)

###### Bytes 7, 8, 9 (VBR & Bitrate Formula):
- `Byte 7 & 0x80`: VBR Supported flag (`1` = Variable Bit Rate supported, `0` = Constant Bit Rate only).
- **23-Bit Bitrate Calculation:**
  ```python
  bitrate = ((byte7 & 0x7F) << 16) | (byte8 << 8) | byte9
  ```
  *(If bitrate is 0, it indicates an unspecified or dynamic variable bitrate)*

###### Real Trace Example (from UGREEN HiTune Max5c):
- **Raw Hex:** `07 08 00 02 80 01 8C 82 00 00`
  - `07 08 00 02`: Header (Category 0x07, LOSC 8, Audio, AAC)
  - `Byte 4 (0x80)`: `1000 0000` -> MPEG-2 AAC LC
  - `Byte 5 (0x01)`: `0000 0001` -> 44.1 kHz
  - `Byte 6 (0x8C)`: `1000 1100` -> Bit 7 (`0x80` = 48 kHz), Bit 3 (`0x08` = 1 Channel), Bit 2 (`0x04` = 2 Channels). Combined frequencies: `44.1/48kHz`, Channels: `1/2`
  - `Byte 7 (0x82)`: `1000 0010` -> Bit 7 is `1` (VBR supported); upper bitrate bits = `0x02`
  - `Bytes 8-9 (0x00 0x00)`: Lower 16 bitrate bits = `0x0000`
  - **Bitrate calculation:** `(0x02 << 16) | 0x0000 = 131072 bps` (128 kbps baseline)
  - **Decoded String:** `CODEC Type: MPEG-2, 4 AAC, Object Type: MPEG-2 AAC LC, Sampling Frequency: 44.1/48kHz, Channels: 1/2, VBR: supported, Bit rate: 131072`

---

##### 3. Sony LDAC — Codec Type `0xFF` (Vendor Specific, LOSC = `0x0A`)

Payload Layout:

```text
Byte 0:      [0x07] Service Category (Media Codec)
Byte 1:      [0x0A] Length of Payload (10 bytes)
Byte 2:      [0x00] Media Type (Audio)
Byte 3:      [0xFF] Codec Type (Vendor Specific)
Bytes 4-7:   [0x2D, 0x01, 0x00, 0x00] Vendor ID: 0x0000012D (Sony Corporation, Little-Endian)
Bytes 8-9:   [0xAA, 0x00]             Codec ID: 0x00AA (LDAC, Little-Endian)
Byte 10:     [0x3C]                   Sample Rates Bitmask:
                                      - Bit 5 (0x20): 44.1 kHz
                                      - Bit 4 (0x10): 48.0 kHz
                                      - Bit 3 (0x08): 88.2 kHz
                                      - Bit 2 (0x04): 96.0 kHz
Byte 11:     [0x07]                   Channel Modes Bitmask:
                                      - Bit 2 (0x04): Stereo
                                      - Bit 1 (0x02): Dual Channel
                                      - Bit 0 (0x01): Mono
```

###### Real Trace Example (from UGREEN HiTune Max5c):
- **Raw Hex:** `07 0A 00 FF 2D 01 00 00 AA 00 3C 07`
  - `2D 01 00 00`: Vendor ID `0x0000012D` = Sony Corporation
  - `AA 00`: Codec ID `0x00AA` = LDAC
  - `3C`: `0011 1100` -> Bits 5, 4, 3, 2 are set -> `44.1/48/88.2/96kHz`
  - `07`: `0000 0111` -> Bits 2, 1, 0 are set -> `Stereo/Dual/Mono`
  - **Decoded String:** `CODEC Type: LDAC, Sampling Frequency: 44.1/48/88.2/96kHz, Channel Mode: Stereo/Dual/Mono`

---

##### 4. Qualcomm aptX / aptX-HD / aptX-LL / FastStream / aptX Adaptive — Codec Type `0xFF`

| Codec | Vendor ID (LE Hex) | Vendor ID (DWORD) | Codec ID (LE Hex) | Codec ID (WORD) | Parameter Byte Interpretation | Formatted Capability String |
|-------|--------------------|-------------------|-------------------|-----------------|-------------------------------|-----------------------------|
| **aptX** | `4F 00 00 00` | `0x0000004F` (CSR) | `01 00` | `0x0001` | Sample Rates: 44.1/48 kHz, Modes: Stereo/Dual | `CODEC Type: aptX, Sampling Frequency: 44.1/48kHz, Channel Mode: Stereo/Dual Channel` |
| **aptX-HD** | `D7 00 00 00` | `0x000000D7` (Qualcomm) | `24 00` | `0x0024` | 24-bit audio, 44.1/48 kHz, Stereo | `CODEC Type: aptX-HD, Sampling Frequency: 44.1/48kHz, Channel Mode: Stereo` |
| **aptX-LL** | `0A 00 00 00` | `0x0000000A` (CSR) | `02 00` | `0x0002` | Low-latency buffer target: ~35ms | `CODEC Type: aptX Low Latency, Sampling Frequency: 44.1/48kHz, Channel Mode: Stereo` |
| **FastStream** | `0A 00 00 00` | `0x0000000A` | `01 00` | `0x0001` | Bi-directional voice backchannel (16 kHz) | `CODEC Type: FastStream, Sampling Frequency: 44.1/48kHz, Channel Mode: Stereo` |
| **aptX Adaptive** | `D7 00 00 00` | `0x000000D7` | `AD 00` / `A7 00` | `0x00AD` | Dynamic 279-420 kbps, 44.1/48/96 kHz | `CODEC Type: aptX Adaptive, Sampling Frequency: 44.1/48/96kHz, Channel Mode: Stereo` |
| **LHDC** | `D6 05 00 00` | `0x000005D6` (Savitech) | `33 4C` | `0x4C33` | Low Latency High-Definition Audio Codec | `CODEC Type: LHDC, Sampling Frequency: 44.1/48/96kHz, Bit depth: 16/24-bit` |

---

#### E. How to Extract Codec Information from Kernel Driver Traces (`.etl`)

The kernel filter driver writes its continuous event trace to `AltA2DP.etl` and `BtTweaker.etl`. Here is the exact algorithm to extract authentic codec capabilities for any device:

##### 1. Binary Structure of ETL Trace Records
ETW files on Windows are structured as 64KB buffers. Within each buffer, event records follow the `EVENT_RECORD` format:
- `EVENT_HEADER`: Contains Provider ID (`{045f889e-3afe-4a8c-be2d-85241829b6e9}`), Timestamp, Thread ID (typically `0x047c` for driver worker threads), and Event ID.
- `UserData`: Contains the raw payload emitted by the driver.

##### 2. The Extraction Algorithm (Session Window Scanning)
Rather than relying on brittle ETW schema DLLs, a direct binary sliding window parser reliably extracts both advertised and active codecs:

```python
import re
import struct

def extract_device_codecs_from_etl(etl_file_path: str, mac_address: str):
    """
    Extracts advertised AVDTP capabilities and active negotiated codec
    from BtTweakerFltr kernel driver trace files.
    """
    # 1. Format MAC into little-endian search pattern
    mac_clean = mac_address.replace(":", "").replace("-", "").lower()
    mac_bytes_be = bytes.fromhex(mac_clean)
    mac_bytes_le = mac_bytes_be[::-1]  # Reverse for little-endian
    
    with open(etl_file_path, "rb") as f:
        data = f.read()
    
    # 2. Locate connection events for this device
    mac_positions = [m.start() for m in re.finditer(re.escape(mac_bytes_le), data)]
    if not mac_positions:
        return []
    
    # 3. Establish temporal session windows around connection points
    WINDOW_SIZE = 64 * 1024  # 64 KB window
    discovered_codecs = []
    
    for pos in mac_positions:
        win_start = max(0, pos - 32 * 1024)
        win_end = min(len(data), pos + WINDOW_SIZE)
        chunk = data[win_start:win_end]
        
        # 4. Scan for AVDTP Category 0x07 Media Codec signatures
        idx = 0
        while idx < len(chunk) - 6:
            # Look for 0x07 (Media Codec) + LOSC + 0x00 (Audio)
            if chunk[idx] == 0x07 and chunk[idx + 2] == 0x00:
                losc = chunk[idx + 1]
                frame_len = 2 + losc
                if 6 <= frame_len <= 16 and idx + frame_len <= len(chunk):
                    raw_frame = chunk[idx : idx + frame_len]
                    codec_type = raw_frame[3]
                    
                    # Validate known codec signatures
                    if codec_type == 0x00:    # SBC (LOSC=6)
                        discovered_codecs.append(("SBC", raw_frame))
                    elif codec_type == 0x02:  # AAC (LOSC=8)
                        discovered_codecs.append(("MPEG-2, 4 AAC", raw_frame))
                    elif codec_type == 0xFF:  # Vendor Specific
                        vendor_id = struct.unpack('<I', raw_frame[4:8])[0]
                        codec_id = struct.unpack('<H', raw_frame[8:10])[0]
                        if vendor_id == 0x12D and codec_id == 0x00AA:
                            discovered_codecs.append(("LDAC", raw_frame))
                        elif vendor_id == 0x4F and codec_id == 0x0001:
                            discovered_codecs.append(("aptX", raw_frame))
                        elif vendor_id == 0xD7 and codec_id == 0x0024:
                            discovered_codecs.append(("aptX-HD", raw_frame))
                    idx += frame_len
                    continue
            idx += 1
            
    return discovered_codecs
```

##### 3. Driver Negotiated Property Events
The driver logs its internal negotiated state as length-prefixed UTF-16 strings followed by little-endian 32-bit integers (`<I`):
- `Codec`: `1` (SBC active), `2` (AAC active), `7` (AVDTP capability handshake event), `0xFF` (Vendor codec active)
- `SbcSamplingFrequency`: `15` (Capability mask: 16, 32, 44.1, 48 kHz), `2` (44.1 kHz selected), `1` (48 kHz selected)
- `SbcChannelMode`: `15` (Capability mask: Mono, Dual, Stereo, Joint Stereo), `4` (Joint Stereo selected)
- `SbcBlockLength`: `15` (Capability mask: 4, 8, 12, 16), `8` (Block length 16 selected), `1` (Block length 4 selected)
- `SbcSubbands`: `3` (Capability mask: 4, 8), `1` (8 subbands selected)
- `SbcAllocationMethod`: `3` (Capability mask: SNR, Loudness), `1` (Loudness selected)
- `SbcMinimumBitpool`: `2`
- `SbcMaximumBitpool`: `38` (or `53`)

---

#### F. Correlating with Live Windows Audio Endpoint (`MMDevices`)

Windows stores the negotiated, real-time playback format for active Bluetooth audio endpoints in the Windows Multimedia Device registry:

- **Registry Path:** `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render\{DEVICE_GUID}\Properties`
- **Format Property Key:** `{f19f064d-082c-4e27-bc73-6882a1bb8e4c},0` (`PKEY_AudioEngine_DeviceFormat`)

The value is a binary `WAVEFORMATEXTENSIBLE` structure:
```python
# Unpack first 16 bytes:
wFormatTag, nChannels, nSamplesPerSec, nAvgBytesPerSec, nBlockAlign, wBitsPerSample = struct.unpack(
    '<HHIIHH', payload[:16]
)
# nSamplesPerSec: e.g. 44100 -> 44.1 kHz, 48000 -> 48.0 kHz
# nChannels: 2 -> Stereo / Joint Stereo, 1 -> Mono
# wBitsPerSample: 16-bit or 24-bit Hi-Res
```
This enables the application to confirm whether Windows is currently streaming at 44.1 kHz or 48.0 kHz in real-time.


---

## 6. Licensing & Activation System

### License Format

Bluetooth Tweaker uses a key-value text payload signed with **RSA-2048**:

```text
licensed_software:Bluetooth Tweaker
license_type:trial
version:01040901
system_address:d8b32f005bde
start:1789904760
expiration:1790509560
signature:81b3b79ab0dc170d56bdcf004a37de0c9a6175577458ba5ae5363724f5a2abcb65db8...
```

For per-device codec views (`TrialCODEC`):
```text
licensed_software:Bluetooth Tweaker (Device - CODEC)
license_type:trial
version:01040901
system_address:d8b32f005bde
device_address:b4e7b3b6ebe8
start:1789904874
expiration:1790509674
signature:05729830c98aedfd75b5864f58a0375716a1ae73e619020493a132fa5d208ae777b8...
```

### Key Security Notes

1. **Kernel Driver Has No License Check:** `BtTweakerFltr.sys` does **not** check or enforce licensing. It reads `UserParams` from the registry and filters Bluetooth packets unconditionally.
2. **License Check Location:** Licensing is enforced purely inside `BtTweakerUI.exe` and `BtTweakerSvc.exe` via Windows BCrypt API (`BCryptImportKeyPair`, `RSAPUBLICBLOB`). Specifically, `BtTweakerSvc.exe` enforces licensing only for **features exposed through `BtTweakerUI.exe`** (the official UI). It does **not** block the kernel driver from operating. `BtTweakerSvc.exe` also manages automatic `LowerFilters` registration for newly-paired Bluetooth devices — but once a device's filter entry exists in the registry, the kernel driver continues functioning regardless of whether the service is running, expired, or stopped.
3. **Custom GUI / Alternative UI:** Because the kernel driver and service consume simple DWORD registry values under `UserParams`, any custom application can manage Bluetooth Tweaker features (Hardware Volume override, Mic Mute, Codec querying) by interacting directly with the registry without needing `BtTweakerUI.exe` or a paid license.
4. **New Device Paired When Service Is Dead:** `BtTweakerFltr.sys` is registered as a `LowerFilter` **per device instance** (confirmed from live registry inspection of `HKLM\SYSTEM\CurrentControlSet\Enum\BTHENUM\...\LowerFilters`). `BtTweakerSvc.exe` normally writes this entry at pairing time. If the service is unavailable, the filter won't be attached to new devices automatically. Our custom GUI resolves this via `ensure_filter_attached(mac)` in [`core/device_manager.py`](core/device_manager.py), which walks all matching BTHENUM PnP instances, checks each instance's `LowerFilters` value, and writes the `BtTweakerFltr` entry if missing (requires admin). After the entry is written, the user must disconnect and reconnect the device for Windows to reload the driver stack with the filter attached.

---

## 7. Building a Custom GUI / Alternative UI

Below is a complete Python script using standard `winreg` and `ctypes` to control Bluetooth Tweaker settings without using the official GUI.

```python
import winreg
import datetime

# Root registry path for Bluetooth Tweaker Parameters
REG_BASE = r"SYSTEM\CurrentControlSet\Services\BtTweakerFltr\Parameters\UserParams"

def mac_to_hex(mac_str: str) -> str:
    """Formats MAC address string into 12-char lowercase hex (e.g. 'B4-E7-B3-B6-EB-E8' -> 'b4e7b3b6ebe8')"""
    return mac_str.replace(":", "").replace("-", "").replace(" ", "").lower()

def set_disable_hardware_volume(mac_address: str, disable: bool):
    """
    Enables or disables hardware volume control for a specific Bluetooth headset.
    disable=True: Forces software volume scaling on Windows (fixes volume jump bugs).
    disable=False: Uses hardware volume control.
    """
    mac_hex = mac_to_hex(mac_address)
    sub_path = f"{REG_BASE}\\DisableHardwareVolume\\{mac_hex}"
    
    try:
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, sub_path)
        winreg.SetValueEx(key, "Next", 0, winreg.REG_DWORD, 1 if disable else 0)
        
        # Write FILETIME timestamp
        now_filetime = int((datetime.datetime.now(datetime.timezone.utc).timestamp() + 11644473600) * 10000000)
        winreg.SetValueEx(key, "Updated", 0, winreg.REG_QWORD, now_filetime)
        
        winreg.CloseKey(key)
        print(f"[+] Successfully {'disabled' if disable else 'enabled'} HW volume for device {mac_hex}")
    except Exception as e:
        print(f"[-] Failed to update registry: {e}")

def set_mic_mute(mac_address: str, mute: bool):
    """Mutes or unmutes the headset microphone stream at the driver level."""
    mac_hex = mac_to_hex(mac_address)
    sub_path = f"{REG_BASE}\\MicMute\\{mac_hex}"
    
    try:
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, sub_path)
        winreg.SetValueEx(key, "Current", 0, winreg.REG_DWORD, 1 if mute else 0)
        winreg.CloseKey(key)
        print(f"[+] Successfully {'muted' if mute else 'unmuted'} microphone for device {mac_hex}")
    except Exception as e:
        print(f"[-] Failed to update mic mute state: {e}")

def get_device_codec_info(mac_address: str):
    """Reads current and requested codec mode for a given device."""
    mac_hex = mac_to_hex(mac_address)
    sub_path = f"{REG_BASE}\\CodecInfo\\{mac_hex}"
    
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_READ)
        current_codec, _ = winreg.QueryValueEx(key, "Current")
        next_codec, _ = winreg.QueryValueEx(key, "Next")
        winreg.CloseKey(key)
        return {"current": current_codec, "next": next_codec}
    except Exception as e:
        return None

if __name__ == "__main__":
    target_mac = "B4-E7-B3-B6-EB-E8"
    print(f"Querying codec info for {target_mac}:", get_device_codec_info(target_mac))
    set_disable_hardware_volume(target_mac, disable=True)
```

---

## 8. Useful PowerShell Commands

### Query Bluetooth Tweaker Service Status
```powershell
Get-Service -Name "BtTweakerSvc"
```

### Inspect Installed Bluetooth Filter Driver Instance
```powershell
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\BtTweakerFltr"
```

### List All Configured Bluetooth Devices & Overrides
```powershell
Get-ChildItem -Path "HKLM:\SYSTEM\CurrentControlSet\Services\BtTweakerFltr\Parameters\UserParams" -Recurse | 
    ForEach-Object {
        [PSCustomObject]@{
            Path  = $_.PSPath.Replace("Microsoft.PowerShell.Core\Registry::HKEY_LOCAL_MACHINE\", "")
            Values = (Get-ItemProperty -Path $_.PSPath | Select-Object -Property * -ExcludeProperty PS*)
        }
    } | Format-Table -AutoSize
```

### Force Disable Hardware Volume for a Device
```powershell
$mac = "b4e7b3b6ebe8"
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\BtTweakerFltr\Parameters\UserParams\DisableHardwareVolume\$mac"
New-Item -Path $regPath -Force | Out-Null
Set-ItemProperty -Path $regPath -Name "Next" -Value 1 -Type DWord
```

---

## Conclusion & Next Steps

1. **Reverse Engineering Outcome:** We have fully unmasked the architecture, component interaction, kernel filter bindings, complete registry schema, and licensing mechanism of Bluetooth Tweaker v1.4.9.
2. **GUI Development:** Since all tweakable options (`DisableHardwareVolume`, `MicMute`, `CodecInfo`) are controlled via `HKLM\SYSTEM\CurrentControlSet\Services\BtTweakerFltr\Parameters\UserParams`, a lightweight alternative GUI (written in Python, C#, or C++) can completely replace `BtTweakerUI.exe` without any licensing restrictions.
