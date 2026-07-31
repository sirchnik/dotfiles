import gdb
import struct

class ARMv8MInfo(gdb.Command):
    """Prints a comprehensive summary of the current ARMv8-M execution state."""

    def __init__(self):
        super(ARMv8MInfo, self).__init__("arm-info", gdb.COMMAND_USER)

    def get_reg(self, reg_name):
        try:
            val = gdb.parse_and_eval(f"${reg_name}")
            return int(val)
        except gdb.error:
            return None

    def read_word_safe(self, address):
        """Safely reads a 32-bit word from physical/target memory without using symbol casting."""
        try:
            inf = gdb.selected_inferior()
            mem = inf.read_memory(address, 4)
            # Unpack 4 bytes as a little-endian 32-bit unsigned integer (<I)
            return struct.unpack("<I", mem)[0]
        except Exception:
            return None

    def invoke(self, arg, from_tty):
        print("\n" + "="*50)
        print("          ARMv8-M EXECUTION STATE SUMMARY          ")
        print("="*50)

        # 1. Read Core Registers
        pc = self.get_reg("pc")
        sp = self.get_reg("sp")
        lr = self.get_reg("lr")
        control = self.get_reg("control")
        ipsr = self.get_reg("ipsr")

        if pc is None:
            print("[Error] Could not read registers. Is the target halted?")
            return

        # 2. Determine Mode (Thread vs Handler)
        is_handler = (ipsr & 0x1FF) if ipsr else 0
        mode_str = f"Handler Mode (Exception #{is_handler})" if is_handler else "Thread Mode"

        # 3. Determine Security State & Active Stack Pointer
        security_str = "Unknown (Check Security Extensions)"
        sp_str = "Unknown"

        if is_handler and lr:
            if (lr & 0xF0000000) == 0xF0000000:
                s_bit = (lr >> 6) & 1
                sp_bit = (lr >> 2) & 1
                security_str = "Secure" if s_bit else "Non-Secure"
                sp_str = "PSP" if sp_bit else "MSP"
        else:
            if control is not None:
                sp_str = "PSP" if (control & 0x2) else "MSP"
                security_str = "Thread (Banked/Current Security State)"

        # 4. Print Execution State
        print(f"  Execution Mode : {mode_str}")
        print(f"  Security State : {security_str}")
        print(f"  Active Stack   : {sp_str}")
        print("-"*50)

        # 5. Core Registers
        print("  Core Registers:")
        print(f"    PC : 0x{pc:08X}")
        print(f"    SP : 0x{sp:08X}")
        print(f"    LR : 0x{lr:08X}")
        if control is not None: print(f"    CONTROL : 0x{control:02X}")
        print("-"*50)

        # 6. Fault Status Registers (SCB) using safe memory reads
        print("  Fault Status Registers (SCB):")
        cfsr = self.get_reg("cfsr") or self.read_word_safe(0xE000ED28)
        hfsr = self.get_reg("hfsr") or self.read_word_safe(0xE000ED2C)
        
        if cfsr is not None and hfsr is not None:
            print(f"    CFSR : 0x{cfsr:08X}")
            print(f"    HFSR : 0x{hfsr:08X}")
            
            # Quick decoded flags if a fault is active
            if hfsr & (1 << 30):
                print("    [!] FORCED HARD FAULT detected.")
            if cfsr & 0xFFFF0000:
                print("    [!] Usage Fault detected.")
            if cfsr & 0x0000FF00:
                print("    [!] Bus Fault detected.")
            if cfsr & 0x000000FF:
                print("    [!] MemManage Fault detected.")
        else:
            print("    Could not read SCB fault registers (Target memory unreadable or protected).")
            
        print("="*50 + "\n")

ARMv8MInfo()
