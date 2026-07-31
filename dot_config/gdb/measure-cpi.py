import gdb
import struct

class MeasureCPI(gdb.Command):
    """Measure CPI of a code block on Cortex-M33 using the correct SysTick instance.
    
    Usage:
      1. (gdb) measure_cpi start
      2. ... Step, run, or continue ...
      3. (gdb) measure_cpi stop
    """

    def __init__(self):
        super(MeasureCPI, self).__init__("measure_cpi", gdb.COMMAND_USER)
        self.start_tick = None
        self.start_pc = None
        self.systick_base = None

    def detect_systick_base(self):
        """Detects if we should use Secure or Non-Secure SysTick based on current PC.
        In ARMv8-M, the MSB/address range of the PC or SAU configuration dictates security.
        We can check if we have access to the Secure SCS. If reading it returns 0 or fails, 
        or if the address space is Non-Secure, we fall back to Non-Secure SysTick.
        """
        # Let's read the Secure SysTick. If it returns 0 or errors out, we are in NS mode.
        try:
            inf = gdb.selected_inferior()
            # Try to read Secure SysTick CSR
            val = struct.unpack("<I", inf.read_memory(0xE002E010, 4))[0]
            if val == 0:
                # Might be RAZ (Read-As-Zero) due to Non-Secure restriction
                return 0xE000E010 # Non-Secure SysTick
            return 0xE002E010     # Secure SysTick
        except Exception:
            return 0xE000E010         # Non-Secure SysTick (fallback)

    def read_reg32(self, address):
        try:
            inf = gdb.selected_inferior()
            mem = inf.read_memory(address, 4)
            return struct.unpack("<I", mem)[0]
        except Exception as e:
            gdb.write(f"Error reading address {hex(address)}: {e}\n")
            return 0

    def write_reg32(self, address, value):
        try:
            inf = gdb.selected_inferior()
            buf = struct.pack("<I", value)
            inf.write_memory(address, buf)
        except Exception as e:
            gdb.write(f"Error writing address {hex(address)}: {e}\n")

    def get_pc(self):
        return int(gdb.parse_and_eval("$pc"))

    def invoke(self, arg, from_tty):
        args = gdb.string_to_argv(arg)
        if len(args) != 1 or args[0].lower() not in ["start", "stop"]:
            gdb.write("Usage: measure_cpi [start | stop]\n")
            return

        action = args[0].lower()

        if action == "start":
            self.do_start()
        elif action == "stop":
            self.do_stop()

    def do_start(self):
        # Auto-detect security state
        self.systick_base = self.detect_systick_base()
        
        state_str = "SECURE" if self.systick_base == 0xE002E010 else "NON-SECURE"
        gdb.write(f"[*] Detected {state_str} execution environment.\n")

        SYST_CSR = self.systick_base + 0x00
        SYST_RVR = self.systick_base + 0x04
        SYST_CVR = self.systick_base + 0x08

        # 1. Disable SysTick
        self.write_reg32(SYST_CSR, 0)
        # 2. Set max reload value (24-bit)
        self.write_reg32(SYST_RVR, 0x00FFFFFF)
        # 3. Clear current value
        self.write_reg32(SYST_CVR, 0)
        # 4. Enable SysTick (Source = Core Clock, Enable = 1)
        self.write_reg32(SYST_CSR, 0x5)

        # Capture start state
        self.start_tick = self.read_reg32(SYST_CVR) & 0x00FFFFFF
        self.start_pc = self.get_pc()
        
        gdb.write(f"[+] Profiling started at PC: {hex(self.start_pc)}\n")

    def do_stop(self):
        if self.start_tick is None or self.systick_base is None:
            gdb.write("[-] Error: Profiling was not started. Run 'measure_cpi start' first.\n")
            return

        SYST_CSR = self.systick_base + 0x00
        SYST_CVR = self.systick_base + 0x08

        # Capture stop state
        stop_tick = self.read_reg32(SYST_CVR) & 0x00FFFFFF
        stop_pc = self.get_pc()

        # Disable SysTick
        self.write_reg32(SYST_CSR, 0)

        # Calculate elapsed cycles (accounting for 24-bit wrap)
        total_cycles = (self.start_tick - stop_tick) & 0x00FFFFFF

        gdb.write("\n================ PROFILE RESULTS ================\n")
        gdb.write(f"  SysTick Used                : {'SECURE' if self.systick_base == 0xE002E010 else 'NON-SECURE'} ({hex(self.systick_base)})\n")
        gdb.write(f"  Start PC                    : {hex(self.start_pc)}\n")
        gdb.write(f"  Stop PC                     : {hex(stop_pc)}\n")
        gdb.write(f"  Total Clock Cycles Elapsed  : {total_cycles}\n")
        gdb.write("=================================================\n")

        # Reset state
        self.start_tick = None
        self.start_pc = None
        self.systick_base = None

# Instantiate command
MeasureCPI()
