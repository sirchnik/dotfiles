import gdb
import struct

class DumpExceptionFrame(gdb.Command):
    """Dumps the hardware stack frame of the pre-empted context during an exception.
    Works for any exception on Arm Cortex-M (ARMv7-M and ARMv8-M with TrustZone).
    """
    def __init__(self):
        super(DumpExceptionFrame, self).__init__("arm-stack-dump", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        # 1. Read the Link Register (LR) to grab the EXC_RETURN payload
        try:
            lr_val = int(gdb.parse_and_eval("$lr"))
        except gdb.error:
            print("Error: Could not read $lr. Is the target halted?")
            return

        # 2. Verify we are actually inside an exception handler
        # EXC_RETURN high bits must be 0xFFFFFFXX or 0xFEFFFFXX
        if (lr_val & 0xFE000000) != 0xFE000000 and (lr_val & 0xFF000000) != 0xFF000000:
            print(f"Error: Not inside an exception handler. LR = {hex(lr_val)}")
            print("EXC_RETURN payload expected in LR (e.g., 0xFFFFFFF9, 0xFXFFFFFF).")
            return

        print(f"\n=== Exception Detected (EXC_RETURN: {hex(lr_val)}) ===")
        
        # 3. Decode ARMv8-M TrustZone / Security Extension Bits
        is_armv8m = (lr_val & (1 << 24)) == 0  # In ARMv8-M, bit 24 is 0 if security extensions are active (0xFE...)
        
        print("Security State Decoding:")
        # Bit 6: Secure / Non-Secure stack
        secure_stack = (lr_val & (1 << 6)) != 0
        print(f"  Pre-empted Stack State : {'Secure' if secure_stack else 'Non-Secure'}")
        
        # Bit 5: Default Callee Register Stacking (ARMv8-M)
        dcrs = (lr_val & (1 << 5)) != 0
        print(f"  Callee Regs Stacked    : {'No (Default rules)' if dcrs else 'Yes (Additional state saved)'}")

        # Bit 4: Frame Type (0 = FPU extended, 1 = Standard basic)
        has_fpu = (lr_val & (1 << 4)) == 0
        print(f"  Frame Type             : {'Extended (FPU registers stacked)' if has_fpu else 'Standard (Basic)'}")

        # Bit 3: Return Mode
        thread_mode = (lr_val & (1 << 3)) != 0
        print(f"  Return Mode            : {'Thread Mode' if thread_mode else 'Handler Mode'}")

        # Bit 2: Stack Pointer Selection
        use_psp = (lr_val & (1 << 2)) != 0
        
        # Bit 0: Exception Security State (ARMv8-M)
        exc_secure = (lr_val & (1 << 0)) != 0
        print(f"  Exception Target State : {'Secure' if exc_secure else 'Non-Secure'}")
        print("-" * 40)

        # 4. Map the target SP register based on Bit 2 and Bit 6 (TrustZone can use Secure/Non-secure bank SPs)
        # For simplicity in standard GDB stubs, $msp and $psp usually map to the active security domain,
        # but we explicitly check what we're fetching.
        if use_psp:
            sp_name = "$psp"
            print("Context Stack Location : Process Stack Pointer (PSP)")
        else:
            sp_name = "$msp"
            print("Context Stack Location : Main Stack Pointer (MSP)")

        try:
            sp_val = int(gdb.parse_and_eval(sp_name))
        except gdb.error:
            print(f"Error: Could not read {sp_name}")
            return

        # 5. Read memory as integers generically
        # Standard frame size is 8 words (32 bytes)
        try:
            mem_bytes = inf = gdb.selected_inferior().read_memory(sp_val, 32)
        except gdb.error:
            print(f"Error: Failed to read memory at {hex(sp_val)}")
            return

        # Unpack the 8 standard registers (Little Endian uint32)
        regs = struct.unpack("<8I", mem_bytes)

        # 6. Output the standard stack frame registers
        print(f"Stack Pointer Base Address: {hex(sp_val)}")
        print(f"  r0   : {hex(regs[0])}")
        print(f"  r1   : {hex(regs[1])}")
        print(f"  r2   : {hex(regs[2])}")
        print(f"  r3   : {hex(regs[3])}")
        print(f"  r12  : {hex(regs[4])}")
        print(f"  lr   : {hex(regs[5])}")
        print(f"  pc   : {hex(regs[6])}  <-- Address that caused/was interrupted by exception")
        print(f"  xPSR : {hex(regs[7])}")

        if has_fpu:
            print("\n[FPU Float Registers (s0-s15 + FPSCR) were also stacked but omitted for brevity]")
        
        # Integrity hint for TrustZone transitions
        if not dcrs:
            print("\n[Notice: Integrity signature and additional callee registers are present on stack due to DCRS=0]")
            
        print("=" * 40)

# Instantiate the command so GDB registers it
DumpExceptionFrame()
