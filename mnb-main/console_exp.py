import contextlib
import sys
import time

import console

class ProgressElement(contextlib.AbstractContextManager):
    def __init__(self, output, descr):
        self.output = output
        self.descr = descr

    def __enter__(self):
        self.output.begin_step(self.descr)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.output.end_step()
x
    def __leave__(self):
        self.output.end_step()

    def progress(self, message):
        self.output.update_step(self.descr, message)

    def fail(self, message):
        self.output.failed_step(self.descr, message)

    def success(self, message):
        self.output.success_step(self.descr, message)

class ConsoleOutput:
    def __init__(self):
        no_style = lambda x: xx
        self.s_descr_progress = console.fg.lightblue
        self.s_descr_failed = console.fg.red
        self.s_descr_success = console.fg.green
        self.s_message_progress = console.fg.white
        self.s_message_failed = no_style
        self.s_message_success = no_style
        self.last_length = 0
        self.file = sys.stdout

    def begin_step(self, descr):
        line = f"  ${self.s_descr_progress(descr)}"
        self._line(line)

    def end_step(self):
        print(file=self.file, flush=True)

    def update_step(self, descr, message):
        self._clear()
        self._line(f"  {self.s_descr_progress(descr)}: {self.s_message_progress(message)}")

    def failed_step(self, descr, message):
        self._clear()
        self._line(f"• {self.s_descr_failed(descr)}: {self.s_message_failed(message)}")

    def success_step(self, descr, message):
        self._clear()
        self._line(f"• {self.s_descr_success(descr)}: {self.s_message_success(message)}")

    def _line(self, line):
        self.last_length = len(line)
        print("\r" + line, file=self.file, end='', flush=True)

    def _clear(self):
        print(f"\r{' ' * self.last_length}", end='')
        self.last_length = 0

#◦○●•∙・❖◆✓˟
output = ConsoleOutput()
for i in range(1,11):
    with ProgressElement(output, f"step {i}") as step:
        for j in range(0, 8):
            step.progress(f'part {j} in progress')
            time.sleep(0.1)
        if i % 4 == 0:
            step.fail("failed")
        else:
            step.success("success")
