from ..assembler import Assembler, AssemblerResult
from .libmac65 import mac65_assemble

class MAC65(Assembler):
    name = "mac65"
    ui_name = "MAC/65 (ATasm)"
    cpu = "6502"

    comment_char = ";"
    origin = "*="
    data_byte = ".byte"
    data_byte_prefix = "$"
    data_byte_separator = ", "

    def __init__(self, verbose=False):
        Assembler.__init__(self, verbose)
        self.current_parser = self.null_parser

    def assemble(self, source):
        if isinstance(source, str):
            source = source.encode("utf-8")
        result = AssemblerResult()
        errors, text = mac65_assemble(source)
        errors = errors.strip()
        if errors:
            result.errors = [errors]
        self.current_parser = self.null_parser
        if text:
            self.parse(result, text)
        return result

    def null_parser(self, result, line, cleanup=False):
        pass

    def source_parser(self, result, line, cleanup=False):
        if cleanup:
            if result.first_addr is None:
                return
            if self.verbose: print("Code block: %x-%x" % (result.first_addr, result.last_addr))
            result.segments.append((result.first_addr, result.last_addr, result.current_bytes))
            result.first_addr = None
            result.last_addr = None
            result.current_bytes = []
            return

        lineno, addr, data, text = line[0:5], line[6:10], line[12:30], line[30:]
        addr = int(addr, 16)
        b = [int(a,16) for a in data.split()]
        #print hex(index), b
        if b:
            count = len(b)
            if result.first_addr is None:
                result.first_addr = result.last_addr = addr
            elif addr != result.last_addr:
                if self.verbose: print("Code block: %x-%x" % (result.first_addr, result.last_addr))
                result.segments.append((result.first_addr, result.last_addr, result.current_bytes))
                result.first_addr = result.last_addr = addr
                result.current_bytes = []

            result.current_bytes.extend(b)
            result.last_addr += count

            try:
                code_type = self.code_type_at_line[lineno]
            except KeyError:
                directive = text.strip()
                if len(directive) == len(text):
                    # label
                    print("LABEL!!!", lineno, text)
                    if len(text) > 0:
                        _, directive = text.split(None, 1)
                    else:
                        directive = ".byte"
                if directive.startswith("."):
                    if directive == ".word":
                        code_type = "w"
                    else:
                        code_type = "b"
                else:
                    code_type = "code"
                self.code_type_at_line[lineno] = code_type
            for i in range(count):
                result.addr_type_code[addr + i] = code_type
            if self.verbose: print(f"line: {addr:04x}, {text}")

    def equates_parser(self, result, line, cleanup=False):
        if cleanup:
            return
        symbol, addr = line.split(": ")
        if symbol[0] == "*":
            result.transitory_equates[symbol[1:].lower()] = int(addr, 16)
        else:
            result.equates[symbol.lower()] = int(addr, 16)

    def symbol_parser(self, result, line, cleanup=False):
        if cleanup:
            return
        symbol, addr = line.split(": ")
        result.add_label(symbol, addr)

    def parse(self, result, text):
        self.code_type_at_line = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if self.verbose: print("parsing:", line)
            if line.startswith("Source:"):
                self.current_parser(result, None, cleanup=True)
                self.current_parser = self.source_parser
            elif line == "Equates:":
                self.current_parser(result, None, cleanup=True)
                self.current_parser = self.equates_parser
            elif line == "Symbol table:":
                self.current_parser(result, None, cleanup=True)
                self.current_parser = self.symbol_parser
            else:
                self.current_parser(result, line)
        result.generate_data_info()
