import gdb

class MeasureTo(gdb.Command):
    """
    Measures instruction count from the current PC to a target symbol or address.
    Optimized to disable TUI, disassembly, and symbol lookups during execution.
    """
    def __init__(self):
        super(MeasureTo, self).__init__("measure_to", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print("Error: Please provide a target end address or symbol.")
            return

        target_addr = None
        arg_stripped = arg.strip()

        # 1. Resolve target symbol/address
        try:
            symbol, _ = gdb.lookup_symbol(arg_stripped)
            if symbol is not None:
                value = symbol.value()
                if value.type.code == gdb.TYPE_CODE_FUNC:
                    target_addr = int(value.address)
                else:
                    target_addr = int(value)
        except Exception:
            pass

        if target_addr is None:
            try:
                eval_str = arg_stripped
                if "::" in eval_str and not (eval_str.startswith("'") or eval_str.startswith('"')):
                    eval_str = f"'{eval_str}'"
                target_addr = int(gdb.parse_and_eval(eval_str))
            except Exception as e:
                print(f"Error: Could not resolve target '{arg_stripped}' ({e})")
                return

        print(f"Measuring... [Target: {arg_stripped} ({hex(target_addr)})]")

        # --- SAVE CURRENT GDB SETTINGS ---
        prev_pagination = gdb.parameter("pagination")
        prev_disassemble = gdb.parameter("disassemble-next-line")
        prev_print_symbol = gdb.parameter("print symbol")
        
        # Check if TUI (Text User Interface) is active and disable it
        tui_active = False
        try:
            # If this succeeds, TUI is enabled
            if gdb.execute("tui status", to_string=True).strip() != "TUI mode is disable.":
                tui_active = True
                gdb.execute("tui disable")
        except gdb.error:
            pass # TUI not supported or already off

        # --- DISABLE ALL OVERHEAD ---
        gdb.execute("set pagination off")
        gdb.execute("set disassemble-next-line off")
        gdb.execute("set print symbol off")

        instruction_count = 0
        
        try:
            # Cache Python lookup functions to save microsecond overhead in the loop
            eval_pc = gdb.parse_and_eval
            step_instruction = gdb.execute

            while True:
                current_pc = int(eval_pc("$pc"))

                if current_pc == target_addr:
                    break

                # stepi output is captured to a string and immediately discarded
                step_instruction("stepi", to_string=True)
                instruction_count += 1

                # Safeguard limit (10 million instructions)
                if instruction_count > 10000000:
                    print("Execution exceeded 10,000,000 instructions. Aborting.")
                    break

            print("\n--- Measurement Result ---")
            print(f"Reached Target: {arg_stripped} ({hex(target_addr)})")
            print(f"Instructions executed: {instruction_count}")
            print("--------------------------")

        finally:
            # --- RESTORE ALL GDB SETTINGS ---
            gdb.execute(f"set pagination {'on' if prev_pagination else 'off'}")
            gdb.execute(f"set disassemble-next-line {prev_disassemble}")
            gdb.execute(f"set print symbol {'on' if prev_print_symbol else 'off'}")
            if tui_active:
                gdb.execute("tui enable")

# Register the command
MeasureTo()
