import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

def set_global_continue(continuation):
    global __global_continue
    __global_continue = continuation

def get_global_continue():
    return __global_continue
