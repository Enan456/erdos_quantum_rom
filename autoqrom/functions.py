"""Test function library for QROM sweep."""


def get_test_functions(n, d):
    """
    Return a list of (name, callable) test functions f: F_2^n -> F_2^d.

    Three functions that exercise different circuit patterns:
      1. bijection: f(x) = (2x+1) mod 2^d  -- all output patterns
      2. identity:  f(x) = x mod 2^d        -- structured baseline
      3. constant:  f(x) = 2^d - 1          -- all output bits fire
    """
    D = 1 << d
    N = 1 << n

    funcs = [
        ("bijection", lambda x, _D=D: (2 * x + 1) % _D),
        ("identity", lambda x, _D=D: x % _D),
        ("constant", lambda x, _D=D: _D - 1),
    ]
    return funcs
