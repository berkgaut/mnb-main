import sys


def INFO(s):
    log('INFO', s)

def WARN(s):
    log('INFO', s)

def ERROR(s):
    log('ERROR', s)

def log(level, s):
    sys.stderr.write("[%s] %s\n" % (level, s))
    sys.stderr.flush()