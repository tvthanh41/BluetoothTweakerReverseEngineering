import subprocess
import winreg
from typing import Dict, Any


class ServiceMonitor:
    """
    Checks the real-time status of BtTweakerSvc and the BtTweakerFltr.sys kernel driver.
    """

    SERVICE_NAME = "BtTweakerSvc"
    DRIVER_NAME = "BtTweakerFltr"

    @staticmethod
    def get_status() -> Dict[str, Any]:
        result = {
            "service_installed": False,
            "service_running": False,
            "service_status": "Stopped",
            "driver_installed": False,
            "driver_active": False,
            "driver_status": "Not Loaded"
        }

        # 1. Check Service via PowerShell Get-Service (fast and reliable)
        try:
            cmd = f"Get-Service -Name '{ServiceMonitor.SERVICE_NAME}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status"
            out = subprocess.check_output(["powershell", "-NoProfile", "-Command", cmd], stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW).decode().strip()
            if out:
                result["service_installed"] = True
                result["service_status"] = out
                result["service_running"] = (out.lower() == "running")
        except Exception:
            pass

        # 2. Check Driver Status in Registry
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SYSTEM\CurrentControlSet\Services\{ServiceMonitor.DRIVER_NAME}", 0, winreg.KEY_READ)
            result["driver_installed"] = True
            winreg.CloseKey(k)
        except Exception:
            pass

        # 3. Check Driver Active Instances (Enum)
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SYSTEM\CurrentControlSet\Services\{ServiceMonitor.DRIVER_NAME}\Enum", 0, winreg.KEY_READ)
            count, _ = winreg.QueryValueEx(k, "Count")
            if count > 0:
                result["driver_active"] = True
                result["driver_status"] = f"Active ({count} attached nodes)"
            else:
                result["driver_status"] = "Idle (0 attached nodes)"
            winreg.CloseKey(k)
        except Exception:
            if result["driver_installed"]:
                result["driver_status"] = "Installed (Filter Registered)"

        return result

    @staticmethod
    def start_service() -> bool:
        try:
            cmd = f"Start-Service -Name '{ServiceMonitor.SERVICE_NAME}'"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except Exception as e:
            print(f"[-] Failed to start service: {e}")
            return False

    @staticmethod
    def restart_service() -> bool:
        try:
            cmd = f"Restart-Service -Name '{ServiceMonitor.SERVICE_NAME}'"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except Exception as e:
            print(f"[-] Failed to restart service: {e}")
            return False
