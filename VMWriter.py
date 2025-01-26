class VMWriter:
    """
    Writes VM commands to an output .vm file.
    """
    def __init__(self, output_file):
        self.output = open(output_file, 'w')

    def writePush(self, segment, index):
        self.output.write(f"push {segment} {index}\n")

    def writePop(self, segment, index):
        self.output.write(f"pop {segment} {index}\n")

    def writeArithmetic(self, command):
        # e.g. add, sub, neg, eq, gt, lt, and, or, not
        self.output.write(f"{command}\n")

    def writeLabel(self, label):
        self.output.write(f"label {label}\n")

    def writeGoto(self, label):
        self.output.write(f"goto {label}\n")

    def writeIf(self, label):
        self.output.write(f"if-goto {label}\n")

    def writeCall(self, name, nArgs):
        self.output.write(f"call {name} {nArgs}\n")

    def writeFunction(self, name, nLocals):
        self.output.write(f"function {name} {nLocals}\n")

    def writeReturn(self):
        self.output.write("return\n")

    def close(self):
        self.output.close()
