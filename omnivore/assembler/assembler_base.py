class AssemblerResult:
    def __init__(self):
        self.errors = []
        self.segments = []
        self.transitory_equates = {}
        self.equates = {}
        self.labels = {}


class AssemblerBase:
    name = "<base>"
    ui_name = "<pretty name>"
    cpu = "<cpu>"

    comment_char = ";"
    origin = "*="
    data_byte = ".byte"
    data_byte_prefix = "$"
    data_byte_separator = ", "

    def __init__(self, verbose=False):
        self.verbose = verbose

    def assemble(self, source):
        return AssemblerResult()

