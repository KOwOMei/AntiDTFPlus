import sys
import win32serviceutil
from src.auto_service import AntiDTFPlusService

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(AntiDTFPlusService)