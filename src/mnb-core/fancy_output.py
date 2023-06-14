import console

#◦○●•∙・❖◆✓˟

class FancyOutput:
    def __init__(self, file):
        self.s_descr_progress = console.fg.lightblue
        self.s_descr_failed = console.fg.red
        self.s_descr_success = console.fg.green
        self.s_phase = console.fg.white + console.fx.underline
        self.s_prefix = console.fg.yellow
        self.file = file

    def phase(self, text):
        print(self.s_phase(text), file=self.file, flush=True)

    def progress(self, text, prefix = None):
        if prefix:
            print(self.s_prefix(prefix), file=self.file, end='')
        print(self.s_descr_progress(text), file=self.file, flush=True)

    def success(self, text, prefix = None):
        if prefix:
            print(self.s_prefix(prefix), file=self.file, end='')
        print(self.s_descr_success(text), file=self.file, flush=True)

    def failure(self, text, prefix = None):
        if prefix:
            print(self.s_prefix(prefix), file=self.file, end='')
        print(self.s_descr_failed(text), file=self.file, flush=True)
