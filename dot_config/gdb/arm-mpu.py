import gdb

class CheckMpuCmd(gdb.Command):
    """Prints the ARMv8-M MPU Configuration in a readable format.
    Works independently of the current language context (Rust/C)."""

    def __init__(self):
        super(CheckMpuCmd, self).__init__("arm-mpu", gdb.COMMAND_USER)

    def read_reg(self, addr):
        try:
            inferior = gdb.selected_inferior()
            val_bytes = inferior.read_memory(addr, 4)
            return int.from_bytes(val_bytes, byteorder='little')
        except gdb.error as e:
            gdb.write(f"Error reading address 0x{addr:08X}: {e}\n")
            return None

    def write_reg(self, addr, val):
        try:
            inferior = gdb.selected_inferior()
            # Convert python integer to 4-byte little-endian array
            val_bytes = val.to_bytes(4, byteorder='little')
            inferior.write_memory(addr, val_bytes)
            return True
        except gdb.error as e:
            gdb.write(f"Error writing address 0x{addr:08X}: {e}\n")
            return False

    def invoke(self, arg, from_tty):
        # ARMv8-M MPU Register Base Addresses
        MPU_BASE = 0xE000ED90
        MPU_TYPE = MPU_BASE + 0x00
        MPU_CTRL = MPU_BASE + 0x04
        MPU_RNR  = MPU_BASE + 0x08
        MPU_RBAR = MPU_BASE + 0x0C
        MPU_RLAR = MPU_BASE + 0x10

        ctrl = self.read_reg(MPU_CTRL)
        m_type = self.read_reg(MPU_TYPE)

        if ctrl is None or m_type is None:
            gdb.write("Could not read MPU registers. Is the target connected?\n")
            return

        # Decode MPU_TYPE
        dregion = (m_type >> 8) & 0xFF
        gdb.write("=== MPU Global Status ===\n")
        gdb.write(f"Total MPU Regions Supported: {dregion}\n")

        # Decode MPU_CTRL
        enabled = ctrl & 0x1
        hfnmiena = (ctrl >> 1) & 0x1
        privdefena = (ctrl >> 2) & 0x1
        
        gdb.write(f"MPU Enabled: {'YES' if enabled else 'NO'}\n")
        gdb.write(f"HardFault/NMI Handler Enable (HFNMIENA): {hfnmiena}\n")
        gdb.write(f"Default Memory Map as Background (PRIVDEFENA): {privdefena}\n\n")

        if not enabled:
            gdb.write("MPU is disabled. Skipping region breakdown.\n")
            return

        gdb.write("=== Active MPU Regions ===\n")
        gdb.write(f"{'Region':<8}{'Base Address':<15}{'Limit Address':<15}{'XN':<5}{'AttrIndex':<10}\n")
        gdb.write("-" * 55 + "\n")

        # Save current RNR so we can restore it later
        original_rnr = self.read_reg(MPU_RNR)

        # Iterate through regions to find active ones
        for r in range(dregion):
            # Select the region by writing raw bytes to MPU_RNR
            if not self.write_reg(MPU_RNR, r):
                break

            rbar = self.read_reg(MPU_RBAR)
            rlar = self.read_reg(MPU_RLAR)

            if rbar is None or rlar is None:
                continue

            # In ARMv8-M, a region is enabled if the EN bit (bit 0) of RLAR is set
            region_enabled = rlar & 0x1

            if region_enabled:
                base_addr = rbar & 0xFFFFFFE0
                # ARMv8-M regions are 32-byte aligned; Limit address adds the lower bits
                limit_addr = (rlar & 0xFFFFFFE0) | 0x1F  
                xn = (rbar >> 0) & 0x1  # Execute Never bit
                ap = (rbar >> 1) & 0x3  # Access Permissions
                attr_idx = (rlar >> 1) & 0x7 # Attribute Index pointing to MPU_MAIR0/1

                # Decode Access Permissions (AP)
                ap_str = {
                    0: "RW Priv / None Unpriv",
                    1: "RW Priv / RW Unpriv",
                    2: "RO Priv / None Unpriv",
                    3: "RO Priv / RO Unpriv"
                }.get(ap, "Unknown")

                gdb.write(f"{r:<8}0x{base_addr:08X}    0x{limit_addr:08X}    {'Yes' if xn else 'No':<5}{attr_idx:<10}\n")
                gdb.write(f"         └─ Permissions: {ap_str}\n")

        # Restore original RNR state
        if original_rnr is not None:
            self.write_reg(MPU_RNR, original_rnr)

# Register the command with GDB
CheckMpuCmd()
