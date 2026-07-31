import gdb

class ArmIrqsCommand(gdb.Command):
    """Dumps all relevant information from the ARMv8-M NVIC and SysTick timers.
    Usage: arm-irqs"""

    def __init__(self):
        super(ArmIrqsCommand, self).__init__("arm-nvic", gdb.COMMAND_DATA)

    def invoke(self, arg, from_tty):
        # Base addresses for NVIC and SysTick (Assuming execution in Secure state to see both views)
        NVIC_BASE      = 0xE000E000
        S_SYSTICK_BASE = 0xE000E010  # Secure SysTick (or Default if Security Extension absent)
        NS_SYSTICK_BASE = 0xE002E010  # Non-Secure SysTick alias

        # Helper to read a 32-bit physical/memory address
        def read_u32(addr):
            try:
                # Use inferior memory reading to bypass symbol requirements
                val_bytes = gdb.selected_inferior().read_memory(addr, 4)
                return int.from_bytes(val_bytes, byteorder='little')
            except Exception:
                # If memory is unmapped or inaccessible (e.g. NS_SYSTICK when not in Secure state)
                return None

        def format_systick(base_addr, name):
            ctrl = read_u32(base_addr + 0x00)
            load = read_u32(base_addr + 0x04)
            val  = read_u32(base_addr + 0x08)
            calib = read_u32(base_addr + 0x0C)

            if ctrl is None:
                return f"{name:<15} [Inaccessible / Not Present]"

            enabled = "Enabled" if (ctrl & 0x1) else "Disabled"
            tickint = "Interrupt" if (ctrl & 0x2) else "No-Interrupt"
            clk_src = "Core Clock" if (ctrl & 0x4) else "External Ref"
            countflag = "Yes" if (ctrl & 0x10000) else "No"
            
            return (f"{name:<15} State: {enabled:<8} | Mode: {tickint:<12} | "
                    f"Src: {clk_src:<10} | Val: 0x{val:06X}/0x{load:06X} | Counted: {countflag}")

        # 1. SysTick Status Output
        print("=" * 75)
        print("ARMv8-M SysTick Timers State")
        print("=" * 75)
        print(format_systick(S_SYSTICK_BASE, "Secure SysTick"))
        print(format_systick(NS_SYSTICK_BASE, "NS SysTick"))
        print()

        # 2. Read ICTR to get total lines
        ictr = read_u32(NVIC_BASE + 0x004)
        if ictr is None:
            print("Error: Could not read NVIC configuration registers.")
            return

        int_lines_num = ictr & 0xF
        num_regs = int_lines_num + 1
        total_interrupts = num_regs * 32

        print("=" * 75)
        print(f"ARMv8-M NVIC Configuration (Base: 0x{NVIC_BASE:08X})")
        print(f"ICTR.INTLINESNUM: {int_lines_num} ({num_regs} register blocks, up to {total_interrupts} interrupts)")
        print("=" * 75)
        print(f"{'IRQ':<6} {'State':<10} {'Pending':<9} {'Active':<8} {'Priority':<10} {'Security (ITNS)':<15}")
        print("-" * 75)

        # 3. Bulk read the register arrays based on the active blocks
        iser = [read_u32(NVIC_BASE + 0x100 + (i * 4)) or 0 for i in range(num_regs)]
        ispr = [read_u32(NVIC_BASE + 0x200 + (i * 4)) or 0 for i in range(num_regs)]
        iabr = [read_u32(NVIC_BASE + 0x300 + (i * 4)) or 0 for i in range(num_regs)]
        
        itns_regs_needed = (total_interrupts + 31) // 32
        itns = [read_u32(NVIC_BASE + 0x380 + (i * 4)) or 0 for i in range(itns_regs_needed)]
        ipr = [read_u32(NVIC_BASE + 0x400 + (i * 4)) or 0 for i in range((total_interrupts + 3) // 4)]

        # 4. Process and print status for each individual interrupt line
        for irq in range(total_interrupts):
            block = irq // 32
            bit_mask = 1 << (irq % 32)

            # Check status flags
            is_enabled = "Enabled" if (iser[block] & bit_mask) else "Disabled"
            is_pending = "Yes" if (ispr[block] & bit_mask) else "No"
            is_active = "Yes" if (iabr[block] & bit_mask) else "No"

            # Parse Priority from IPR
            ipr_reg_idx = irq // 4
            ipr_byte_offset = irq % 4
            ipr_val = ipr[ipr_reg_idx]
            priority = (ipr_val >> (ipr_byte_offset * 8)) & 0xFF

            # Parse Security Configuration (ITNS)
            # Bit set => Non-Secure, Bit clear => Secure
            is_ns = (block < len(itns)) and (itns[block] & bit_mask)
            security = "Non-Secure" if is_ns else "Secure"

            # Optimization filter to keep terminal output clean
            if (iser[block] & bit_mask) or (ispr[block] & bit_mask) or (iabr[block] & bit_mask) or priority != 0 or is_ns:
                print(f"{irq:<6} {is_enabled:<10} {is_pending:<9} {is_active:<8} {priority:<10} {security:<15}")

        print("=" * 75)

# Instantiate the command
ArmIrqsCommand()
