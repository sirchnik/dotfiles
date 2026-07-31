import gdb

class ArmSauCommand(gdb.Command):
    """Dump all ARMv8-M Security Attribution Unit (SAU) configuration and region data (Rust target)."""

    def __init__(self):
        super(ArmSauCommand, self).__init__("arm-sau", gdb.COMMAND_DATA)

    def invoke(self, arg, from_tty):
        # PPB (Private Peripheral Block) base address for SAU
        # SAU_CTRL is located at 0xE000EDD0
        SAU_BASE = 0xE000EDD0

        try:
            # Read Base Registers using Rust raw pointer casting syntax
            ctrl = int(gdb.parse_and_eval(f"*({SAU_BASE} as *const u32)"))
            sau_type = int(gdb.parse_and_eval(f"*({SAU_BASE + 0x4} as *const u32)"))
            sfsr = int(gdb.parse_and_eval(f"*({SAU_BASE + 0x14} as *const u32)"))
            sfar = int(gdb.parse_and_eval(f"*({SAU_BASE + 0x18} as *const u32)"))
        except gdb.error as e:
            gdb.write(f"Error: Could not read SAU registers ({e}). Is the target connected and halted?\n")
            return

        # Parse CTRL
        enabled = ctrl & 0x1
        allns = (ctrl >> 1) & 0x1

        # Parse TYPE (Number of regions supported)
        max_regions = sau_type & 0xFF

        gdb.write("==================================================\n")
        gdb.write("          ARMv8-M SAU CONFIGURATION DUMP          \n")
        gdb.write("==================================================\n")
        gdb.write(f"SAU Status:      {'ENABLED' if enabled else 'DISABLED'}\n")
        gdb.write(f"Default Memory:  {'Non-Secure' if allns else 'Secure'}\n")
        gdb.write(f"Max Regions:     {max_regions}\n")
        gdb.write(f"SFSR Status:     0x{sfsr:08X}\n")
        if sfsr & (1 << 6): # SFARVALID bit
            gdb.write(f"SFAR Address:    0x{sfar:08X}\n")
        gdb.write("--------------------------------------------------\n\n")

        if max_regions == 0:
            gdb.write("No hardware SAU regions implemented.\n")
            return

        gdb.write(f"{'Region':<8}{'Status':<10}{'Base Address':<15}{'Limit Address':<15}{'Type':<12}\n")
        gdb.write("-" * 65 + "\n")

        # Pointers to RNR, RBAR, and RLAR
        RNR_ADDR  = SAU_BASE + 0x8
        RBAR_ADDR = SAU_BASE + 0xC
        RLAR_ADDR = SAU_BASE + 0x10

        # Save current RNR to restore it later
        original_rnr = int(gdb.parse_and_eval(f"*({RNR_ADDR} as *const u32)")) & 0xFF

        for region_id in range(max_regions):
            # Write region index to RNR
            gdb.execute(f"set *({RNR_ADDR} as *mut u32) = {region_id}")

            # Read back RBAR and RLAR for this region
            rbar = int(gdb.parse_and_eval(f"*({RBAR_ADDR} as *const u32)"))
            rlar = int(gdb.parse_and_eval(f"*({RLAR_ADDR} as *const u32)"))

            region_enabled = rlar & 0x1
            nsc = (rlar >> 1) & 0x1
            
            # Mask out the lower 5 bits (OFFSET 5 from your Rust bitfields)
            base_addr = rbar & 0xFFFFFFE0
            limit_addr = (rlar & 0xFFFFFFE0) | 0x1F # Include the 32-byte alignment block

            status_str = "ENABLED" if region_enabled else "DISABLED"
            type_str = "Non-Secure Callable (NSC)" if nsc else "Non-Secure (NS)"

            if region_enabled:
                gdb.write(f"{region_id:<8}{status_str:<10}0x{base_addr:08X}    0x{limit_addr:08X}    {type_str}\n")
            else:
                gdb.write(f"{region_id:<8}{status_str:<10}{'-':<15}{'-':<15}{'-':<12}\n")

        # Restore original RNR
        gdb.execute(f"set *({RNR_ADDR} as *mut u32) = {original_rnr}")
        gdb.write("==================================================\n")

# Instantiate the command class
ArmSauCommand()
