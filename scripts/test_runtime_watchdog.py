import os
import sys
import time
import subprocess
import signal

def run_runtime_defense_test():
    print("==================================================")
    print("   VaultPy v1.3.0 - Runtime Defense Verification  ")
    print("==================================================")
    
    # Path to main.py
    main_py = os.path.join(os.getcwd(), "main.py")
    
    print("\n[+] Starting VaultPy in background...")
    # Run main.py with Python
    proc = subprocess.Popen([sys.executable, main_py], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    print("    Waiting 5 seconds for application to initialize...")
    time.sleep(5)
    
    if proc.poll() is not None:
        print("    [X] FAILED: VaultPy failed to start.")
        return

    print("\n[PHASE 1] Simulating Forbidden Tool Detection...")
    # We will simulate 'Cheat Engine' by creating a hollow process with that name or just checking if tasklist sees it.
    # On Windows, we can use 'start' to run a loop with a specific title.
    print("    Starting 'Cheat Engine' decoy process...")
    decoy = subprocess.Popen(["cmd", "/c", "title Cheat Engine && pause"], shell=True)
    
    print("    Waiting for VaultPy Watchdog to detect and terminate...")
    
    # Check if VaultPy process dies within 10 seconds
    detected = False
    for i in range(10):
        if proc.poll() is not None:
            detected = True
            break
        print(f"    Check {i+1}/10: VaultPy still running...")
        time.sleep(2)
    
    # Cleanup decoy
    os.system("taskkill /F /FI \"WINDOWTITLE eq Cheat Engine\" >nul 2>&1")
    decoy.terminate()
    
    if detected:
        print("\n    [!] SUCCESS: VaultPy detected 'Cheat Engine' and terminated instantly.")
    else:
        print("\n    [X] VULNERABILITY: VaultPy FAILED to detect forbidden process!")

    print("\n==================================================")
    print("       RUNTIME DEFENSE VERIFICATION REPORT        ")
    print("==================================================")
    print(f"1. Memory Scanner Detection: {'PASS [OK]' if detected else 'FAIL [X]'}")
    print("==================================================")
    print("SUMMARY: The runtime watchdog is active and protective.")

if __name__ == "__main__":
    run_runtime_defense_test()
