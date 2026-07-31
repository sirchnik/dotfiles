import gdb
import struct

def ipsr_isr_number_to_str(num):
    mapping = {
        0: "Thread Mode", 1: "Reset", 2: "NMI", 3: "HardFault",
        4: "MemManage", 5: "BusFault", 6: "UsageFault", 7: "SecureFault",
        11: "SVCall", 12: "DebugMonitor", 14: "PendSV", 15: "SysTick"
    }
    return f"External Interrupt {num - 16}" if num >= 16 else mapping.get(num, "Reserved")

class ArmFaultDecode(gdb.Command):
    """Decode ARMv7-M / ARMv8-M exception and fault status registers."""

    def __init__(self):
        super(ArmFaultDecode, self).__init__("arm-fault-info", gdb.COMMAND_USER)

    def read_u32(self, addr):
        try:
            content = gdb.selected_inferior().read_memory(addr, 4)
            return struct.unpack("<I", content)[0]
        except Exception:
            return 0

    def get_symbol_val(self, name):
        for prefix in ["", "&"]:
            try:
                return int(gdb.parse_and_eval(f"{prefix}{name}"))
            except gdb.error:
                continue
        return 0

    def invoke(self, arg, from_tty):
        # Target execution control check
        try:
            current_thread = gdb.selected_thread()
            if current_thread and current_thread.is_running():
                print("Target is running. Sending interrupt...")
                gdb.execute("interrupt", from_tty=False)
        except gdb.error as e:
            print(f"Execution state notice: {e}")

        try:
            faulting_stack = int(gdb.parse_and_eval("$sp"))
        except gdb.error:
            print("Error: Could not read $sp register.")
            return

        # Stack Frame extraction map (Offset, Name)
        reg_offsets = [0, 1, 2, 3, 4, 5, 6, 7]
        vals = [self.read_u32(faulting_stack + i * 4) for i in reg_offsets]
        if any(v is None for v in vals):
            print(f"Error: Failed to read memory at stack 0x{faulting_stack:08X}")
            return
        
        r0, r1, r2, r3, r12, lr, pc, xpsr = vals

        # Read SCB registers
        shcsr = self.read_u32(0xE000ED24)
        cfsr  = self.read_u32(0xE000ED28)
        hfsr  = self.read_u32(0xE000ED2C)
        mmfar = self.read_u32(0xE000ED34)
        bfar  = self.read_u32(0xE000ED38)
        sfsr  = self.read_u32(0xE000ED3C)  # ARMv8-M SecureFault Status Register
        sfar  = self.read_u32(0xE000ED4C)  # SecureFault Address Register

        # Bitfield dictionaries for rapid string evaluation
        cfsr_faults = {
            "Instruction Access Violation": cfsr & (1 << 0),
            "Data Access Violation": cfsr & (1 << 1),
            "Memory Management Unstacking Fault": cfsr & (1 << 3),
            "Memory Management Stacking Fault": cfsr & (1 << 4),
            "Memory Management Lazy FP Fault": cfsr & (1 << 5),
            "Instruction Bus Error": cfsr & (1 << 8),
            "Precise Data Bus Error": cfsr & (1 << 9),
            "Imprecise Data Bus Error": cfsr & (1 << 10),
            "Bus Unstacking Fault": cfsr & (1 << 11),
            "Bus Stacking Fault": cfsr & (1 << 12),
            "Bus Lazy FP Fault": cfsr & (1 << 13),
            "Undefined Instruction Usage Fault": cfsr & (1 << 16),
            "Invalid State Usage Fault": cfsr & (1 << 17),
            "Invalid PC Load Usage Fault": cfsr & (1 << 18),
            "No Coprocessor Usage Fault": cfsr & (1 << 19),
            "Unaligned Access Usage Fault": cfsr & (1 << 24),
            "Divide By Zero": cfsr & (1 << 25),
        }

        sfsr_faults = {
            "Secure Attribution Unit (SAU) Violation": sfsr & (1 << 0),
            "IDAU Violation": sfsr & (1 << 1),
            "Secure Lazy FP Fault": sfsr & (1 << 2),
            "Secure Unstacking Fault": sfsr & (1 << 3),
            "Secure Stacking Fault": sfsr & (1 << 4),
            "Integrity Signature Failure": sfsr & (1 << 5),
            "Target Non-Secure Callable (NSC) Fault": sfsr & (1 << 6),
        }

        # Format Status Registers
        ici_it = (((xpsr >> 25) & 0x3) << 6) | ((xpsr >> 10) & 0x3f)
        exc_num = xpsr & 0x1ff

        output = [
            f"\tr0  0x{r0:x}", f"\tr1  0x{r1:x}", f"\tr2  0x{r2:x}", f"\tr3  0x{r3:x}", f"\tr12 0x{r12:x}", f"\tlr  0x{lr:x}", f"\tpc  0x{pc:x}",
            f"\tpsr 0x{xpsr:x} [ N {(xpsr>>31)&1} Z {(xpsr>>30)&1} C {(xpsr>>29)&1} V {(xpsr>>28)&1} Q {(xpsr>>27)&1} GE {(xpsr>>16)&0xF:04b} ; ICI.IT {ici_it} T {str((xpsr>>24)&1==1).lower()} ; Exc {exc_num}-{ipsr_isr_number_to_str(exc_num)} ]",
            f"\tsp  0x{faulting_stack:x}",
            f"\ttop of stack     0x{self.get_symbol_val('_estack'):x}",
            f"\tbottom of stack  0x{self.get_symbol_val('_sstack'):x}",
            f"\tSHCSR 0x{shcsr:x}\tCFSR  0x{cfsr:x}\tHFSR  0x{hfsr:x}\tSFSR  0x{sfsr:x}\n"
        ]

        # Append decoded faults dynamically
        for desc, hit in cfsr_faults.items():
            output.append(f"\t{desc + ':':<40} {str(bool(hit)).lower()}")
        
        output.append(f"\tBus Fault on Vector Table Read:          {str(bool(hfsr & (1 << 1))).lower()}")
        output.append(f"\tForced Hard Fault:                       {str(bool(hfsr & (1 << 30))).lower()}")
        
        # Append SecureFaults
        for desc, hit in sfsr_faults.items():
            output.append(f"\t{desc + ':':<40} {str(bool(hit)).lower()}")

        # Valid Address Checking Registers
        output.append(f"\tFaulting Memory Address: (valid: {str(bool(cfsr & (1 << 7))).lower()}) 0x{mmfar:08X}")
        output.append(f"\tBus Fault Address:       (valid: {str(bool(cfsr & (1 << 15))).lower()}) 0x{bfar:08X}")
        output.append(f"\tSecure Fault Address:    (valid: {str(bool(sfsr & (1 << 7))).lower()}) 0x{sfar:08X}")

        print("\n".join(output))

ArmFaultDecode()
