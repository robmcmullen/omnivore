from pyatasm_mac65 import mac65_assemble

class Assemble(object):
    def __init__(self, source, verbose=False):
        self.verbose = verbose
        self.errors, text = mac65_assemble(source)
        self.segments = []
        self.transitory_equates = {}
        self.equates = {}
        self.labels = {}
        self.current_parser = self.null_parser
        self.first_addr = None
        self.last_addr = None
        self.current_bytes = []
        if text:
            self.parse(text)

    def __len__(self):
        return len(self.segments)

    def null_parser(self, line, cleanup=False):
        pass

    def source_parser(self, line, cleanup=False):
        if cleanup:
            if self.verbose: print "Code block: %x-%x" % (self.first_addr, self.last_addr)
            self.segments.append((self.first_addr, self.last_addr, self.current_bytes))
            self.first_addr = None
            self.last_addr = None
            self.current_bytes = []
            return

        lineno, addr, data, text = line[0:5], line[6:10], line[12:30], line[31:]
        addr = int(addr, 16)
        b = map(lambda a:int(a,16), data.split())
        #print hex(index), b
        if b:
            count = len(b)
            if self.first_addr is None:
                self.first_addr = self.last_addr = addr
            elif addr != self.last_addr:
                if self.verbose: print "Code block: %x-%x" % (self.first_addr, self.last_addr)
                self.segments.append((self.first_addr, self.last_addr, self.current_bytes))
                self.first_addr = self.last_addr = addr
                self.current_bytes = []

            self.current_bytes.extend(b)
            self.last_addr += count

    def equates_parser(self, line, cleanup=False):
        if cleanup:
            return
        symbol, addr = line.split(": ")
        if symbol[0] == "*":
            self.transitory_equates[symbol[1:].lower()] = int(addr, 16)
        else:
            self.equates[symbol.lower()] = int(addr, 16)

    def symbol_parser(self, line, cleanup=False):
        if cleanup:
            return
        symbol, addr = line.split(": ")
        self.labels[symbol.lower()] = int(addr, 16)

    def parse(self, text):
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if self.verbose: print "parsing:", line
            if line.startswith("Source:"):
                self.current_parser(None, cleanup=True)
                self.current_parser = self.source_parser
            elif line == "Equates:":
                self.current_parser(None, cleanup=True)
                self.current_parser = self.equates_parser
            elif line == "Symbol table:":
                self.current_parser(None, cleanup=True)
                self.current_parser = self.symbol_parser
            else:
                self.current_parser(line)
