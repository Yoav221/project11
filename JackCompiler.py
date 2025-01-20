import os
from CompilationEngine import CompilationEngine

class JackCompiler:
    def __init__(self, input_path):
        """
        Initialize the analyzer with either a .jack file or a directory containing .jack files.
        :param input_path: Path to file or directory
        """
        self.input_path = input_path
        self.files_to_process = []

        # Check if input is a file or directory
        if os.path.isfile(input_path):
            if input_path.endswith('.jack'):
                self.files_to_process.append(input_path)
            else:
                raise ValueError(f"Input file must have .jack extension: {input_path}")
        elif os.path.isdir(input_path):
            # Get all .jack files in the directory
            for file in os.listdir(input_path):
                if file.endswith('.jack'):
                    self.files_to_process.append(os.path.join(input_path, file))
            if not self.files_to_process:
                raise ValueError(f"No .jack files found in directory: {input_path}")
        else:
            raise ValueError(f"Input path does not exist: {input_path}")

    def analyze(self):
        """
        Process all .jack files in self.files_to_process, creating corresponding .xml files.
        """
        for jack_file in self.files_to_process:
            self.process_file(jack_file)

    def process_file(self, jack_file):
        """
        Process a single .jack file by creating a CompilationEngine and calling compile_class().
        """
        output_file = jack_file[:-5] + '.vm'
        engine = CompilationEngine(jack_file, output_file)
        engine.compile_class()
        engine.close()