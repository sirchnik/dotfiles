import gdb

class ProfileCycles(gdb.Command):
    """Measure elapsed clock cycles and estimate executed instructions on Armv8-M targets.
    Usage:
      (gdb) profile-cycles start
      (gdb) continue
      (gdb) profile-cycles stop
    """

    DEMCR = 0xE000EDFC
    DWT_CTRL = 0xE0001000
    DWT_CYCCNT = 0xE0001004
    
    # 8-bit profiling registers
    DWT_CPICNT = 0xE0001008
    DWT_EXCCNT = 0xE000100C
    DWT_SLEEPCNT = 0xE0001010
    DWT_LSUCNT = 0xE0001014
    DWT_FOLDCNT = 0xE0001018

    def __init__(self):
        super(ProfileCycles, self).__init__("profile-cycles", gdb.COMMAND_USER)
        self.baselines = {}

    def read_reg(self, addr, size=4):
        inferior = gdb.selected_inferior()
        try:
            mem = inferior.read_memory(addr, size)
            return int.from_bytes(mem, byteorder='little')
        except gdb.MemoryError:
            gdb.write("Error: Cannot access hardware registers. Is the target halted?\n")
            return None

    def write_reg(self, addr, val, size=4):
        inferior = gdb.selected_inferior()
        bytes_val = int(val).to_bytes(size, byteorder='little')
        try:
            inferior.write_memory(addr, bytes_val)
        except gdb.MemoryError:
            gdb.write(f"Error: Writing to register at {hex(addr)} failed.\n")

    def invoke(self, arg, from_tty):
        args = gdb.string_to_argv(arg)
        if not args or args[0] not in ['start', 'stop']:
            print("Invalid usage. Use 'profile-cycles start' or 'profile-cycles stop'")
            return

        action = args[0]

        if action == 'start':
            # 1. Enable Trace Unit in DEMCR (set bit 24)
            demcr_val = self.read_reg(self.DEMCR)
            if demcr_val is not None:
                self.write_reg(self.DEMCR, demcr_val | 0x01000000)

            # 2. Reset profiling registers (8-bit registers)
            self.write_reg(self.DWT_CYCCNT, 0, 4)
            self.write_reg(self.DWT_CPICNT, 0, 1)
            self.write_reg(self.DWT_EXCCNT, 0, 1)
            self.write_reg(self.DWT_SLEEPCNT, 0, 1)
            self.write_reg(self.DWT_LSUCNT, 0, 1)
            self.write_reg(self.DWT_FOLDCNT, 0, 1)

            # 3. Enable DWT Cycle Counter & all profiling counters (set bit 0 in DWT_CTRL)
            dwt_ctrl_val = self.read_reg(self.DWT_CTRL)
            if dwt_ctrl_val is not None:
                self.write_reg(self.DWT_CTRL, dwt_ctrl_val | 1)

            # Capture baseline for all registers
            self.baselines['CYCCNT'] = self.read_reg(self.DWT_CYCCNT, 4)
            self.baselines['CPICNT'] = self.read_reg(self.DWT_CPICNT, 1)
            self.baselines['EXCCNT'] = self.read_reg(self.DWT_EXCCNT, 1)
            self.baselines['SLEEPCNT'] = self.read_reg(self.DWT_SLEEPCNT, 1)
            self.baselines['LSUCNT'] = self.read_reg(self.DWT_LSUCNT, 1)
            self.baselines['FOLDCNT'] = self.read_reg(self.DWT_FOLDCNT, 1)

            print("Profiling started. Registers cleared and baseline captured.")

        elif action == 'stop':
            if not self.baselines:
                print("Error: Profiling was never started. Run 'profile-cycles start' first.")
                return

            # Read current values
            cur_cyccnt = self.read_reg(self.DWT_CYCCNT, 4)
            cur_cpicnt = self.read_reg(self.DWT_CPICNT, 1)
            cur_exccnt = self.read_reg(self.DWT_EXCCNT, 1)
            cur_sleepcnt = self.read_reg(self.DWT_SLEEPCNT, 1)
            cur_lsucnt = self.read_reg(self.DWT_LSUCNT, 1)
            cur_foldcnt = self.read_reg(self.DWT_FOLDCNT, 1)

            if None in (cur_cyccnt, cur_cpicnt, cur_exccnt, cur_sleepcnt, cur_lsucnt, cur_foldcnt):
                print("Error reading hardware registers.")
                return

            # Handle wraps
            cyccnt = (cur_cyccnt - self.baselines['CYCCNT']) & 0xFFFFFFFF
            cpicnt = (cur_cpicnt - self.baselines['CPICNT']) & 0xFF
            exccnt = (cur_exccnt - self.baselines['EXCCNT']) & 0xFF
            sleepcnt = (cur_sleepcnt - self.baselines['SLEEPCNT']) & 0xFF
            lsucnt = (cur_lsucnt - self.baselines['LSUCNT']) & 0xFF
            foldcnt = (cur_foldcnt - self.baselines['FOLDCNT']) & 0xFF

            # Approximate executed instructions
            instructions = cyccnt - cpicnt - exccnt - sleepcnt - lsucnt + foldcnt

            # Compute CPI (Cycles Per Instruction) safely
            cpi = cyccnt / instructions if instructions > 0 else 0.0

            print("\n" + "="*40)
            print(f" Elapsed Clock Cycles: {cyccnt}")
            print(f" Estimated Instr Executed: {instructions}")
            print(f" Calculated CPI:          {cpi:.3f}")
            print("-"*40)
            print(f" Details (Stalls/Overhead):")
            print(f"  - CPI Stalls (CPICNT):  {cpicnt}")
            print(f"  - LSU Stalls (LSUCNT):  {lsucnt}")
            print(f"  - Exception Overhead:   {exccnt}")
            print(f"  - Folded (FOLDCNT):     +{foldcnt}")
            print("="*40 + "\n")

# Instantiate the command inside GDB
ProfileCycles()
