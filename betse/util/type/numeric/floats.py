#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''
Low-level floating point facilities.
'''

# ....................{ IMPORTS                            }....................
from sys import float_info
# from betse.util.io.log import logs
from betse.util.type.call.memoizers import callable_cached
from betse.util.type.types import type_check, RegexCompiledType

# ....................{ CONSTANTS                          }....................
FLOAT_MIN = float_info.min
'''
Minimum representable finite floating point number under the active Python
interpreter.
'''


FLOAT_MAX = float_info.max
'''
Maximum representable finite floating point number under the active Python
interpreter.
'''

# ....................{ TESTERS                            }....................
@type_check
def is_float_str(text: str) -> bool:
    '''
    ``True`` only if the passed string syntactically conforms to either the
    decimal format (e.g., ``6.669``) or scientific notation format (e.g.,
    ``6.66e9``) expected by floating point numbers.

    Equivalently, this tester returns ``True`` only if this string is losslessly
    convertable into a floating point number.
    '''

    # Avoid circular import dependencies.
    from betse.util.type.text import regexes

    # Return True only if this string matches a floating point format.
    return regexes.is_match(text=text, regex=get_float_regex())

# ....................{ GETTERS                            }....................
@type_check
def get_precision(number: float) -> int:
    '''
    Precision of the passed floating point number.

    Precision is defined as the length of this number's significand (excluding
    leading hidden digit 1), equivalent to the number of base-10 digits in the
    fractional segment of this number *after* accounting for approximation
    errors in floating point arithmetic.

    Examples
    ----------
        >>> from betse.util.type.numeric import floats
        >>> floats.get_precision(0.110001000000000009)
        17
    '''

    # Avoid circular import dependencies.
    from betse.util.type.text import regexes

    # String formatted from this number, guaranteed by Python internals to
    # comply with one of the following two formats:
    #
    # * Decimal notation (e.g., "3.1415").
    # * Scientific notation (e.g., "3.1415e+92", "3.141592e-65").
    number_text = str(number)

    # Scientific notation match groups if this number is in scientific notation,
    # capturing the significand and exponent of this number into these groups.
    number_text_groups = regexes.get_match_groups_named(
        text=number_text, regex=get_float_regex())

    # If this number is in decimal notation...
    if number_text_groups['exponent'] is None:
        # Fractional part of this number if any *OR* the empty string otherwise.
        # Retrieving this substring is complicated by the fact that one of two
        # alternate match groups may yield this substring at a time.
        significand_frac = (
            number_text_groups['significand_frac_empty'] or
            number_text_groups['significand_frac_nonempty'] or '')
        # logs.log_debug('significand (fractional): %s', significand_frac)
        # print('significand (fractional): %s' % significand_frac)

        # This number's precision is the number of digits in this part.
        precision = len(significand_frac)
    # Else, this number is in scientific notation. In this case..
    else:
        # print('exponent: %s' % number_text_groups['exponent'])
        # This number's precision is the absolute value (i.e., ignoring the
        # sign) of this number's exponent in this notation.
        precision = abs(int(number_text_groups['exponent']))

    # Return this precision.
    return precision

# ....................{ GETTERS ~ regex                    }....................
# For efficiency in downstream clients (e.g., BETSEE) frequently calling the
# is_ml() function and hence requiring this expression be compiled, this
# expression is intentionally pre-compiled rather than uncompiled and thus
# returned as a cached getter.

@callable_cached
def get_float_regex() -> RegexCompiledType:
    '''
    Compiled regular expression matching a floating point number represented as
    a string in either decimal notation (e.g., ``6.69``) *or* scientific
    notation (e.g., ``6.6e9``).

    This expression captures the following named match groups (in order):

    1. ``significand``, yielding the mandatory significand of this number
       *including* optional sign prefix (e.g., ``-6.7`` given ``-6.7e-9``).
    1. ``significand_nonfrac_empty``, yielding the optional non-fractional
       digits of this significand *including* optional sign prefix (e.g., ``-6``
       given ``-6.7e-9``). This group's value is ``None`` for numbers prefixed
       by ``.`` rather than a digit (e.g., ``-.67e-9``).
    1. ``significand_frac_nonempty``, alternatively yielding the optional
       fractional digits of this significand in a manner guaranteed to be
       non-empty (e.g., ``None`` given ``-6.7e-9``).
    1. ``significand_frac_empty``, alternatively yielding the optional
       fractional digits of this significand in a manner *not* guaranteed to be
       non-empty (e.g., ``7`` given ``-6.7e-9``). This edge case is required to
       support floating point numbers of both the form
       ``{significand_nonfrac}.{significand_frac_empty}`` *and*
       ``.{significand_frac_nonempty}``. Since the standard :mod:`re` module
       does *not* support the ``(?|...)``-style branch reset syntax supported by
       the third-party :mod:`regex` module, this is the best we can do without
       burdening the codebase with *yet another* third-party dependency.
    1. ``exponent``, yielding the optional exponent of this number *including*
       optional sign prefix (e.g., ``-9`` given ``6.7e-9``).

    See Also
    ----------
    https://jdreaver.com/posts/2014-07-28-scientific-notation-spin-box-pyside.html
        Blog article partially inspiring this implementation.
    https://stackoverflow.com/a/658662/2809027
        StackOverflow answer partially inspiring this implementation.
    '''

    # Avoid circular import dependencies.
    from betse.util.type.text import regexes

    # Create, return, and cache this expression.
    return regexes.compile_regex(
        # Significand (captured).
        r'(?P<significand>'
            # Negative or positive prefix (optional).
            r'[+-]?'
            # Either:
            r'(?:'
            # * Significand prefixed by one or more non-fractional digits.
                # Non-fractional digits.
                r'(?P<significand_nonfrac_empty>\d+)'
                # Fractional digits (optional).
                r'(?:\.(?P<significand_frac_empty>\d*))?'
            r'|'
            # * Significand containing only fractional digits.
                r'\.(?P<significand_frac_nonempty>\d+)'
            r')'
        r')'
        # Exponent (optional).
        r'(?:'
            # Exponent prefix.
            r'[eE]'
            # Exponent (captured).
            r'(?P<exponent>'
                # Exponent sign (optional).
                r'[+-]?'
                # Exponent digits.
                r'\d+'
            r')'
        r')?'
    )


@callable_cached
def _get_float_exponent_regex() -> RegexCompiledType:
    '''
    Compiled regular expression matching the exponent of a floating point number
    represented as a string in scientific notation, typically produced by the
    ``{:g}`` format specifier (e.g., ``6.6e+09``).

    This expression captures the following named match groups (in order):

    1. ``negation``, yielding the optional negative sign prefixing this number's
       exponent if any or the empty string otherwise (e.g., ``-`` given
       ``6.7e-09``).
    1. ``magnitude``, yielding the mandatory magnitude of this number's exponent
       excluding optional prefixing zero (e.g., ``9`` given ``6.7e+09``).

    See Also
    ----------
    https://jdreaver.com/posts/2014-07-28-scientific-notation-spin-box-pyside.html
        Blog article partially inspiring this implementation.
    '''

    # Avoid circular import dependencies.
    from betse.util.type.text import regexes

    # Create, return, and cache this expression.
    return regexes.compile_regex(
        # Exponent prefix.
        r'e'
        # Exponent sign, either:
        r'(?:'
            # Ignorable positive sign. Since exponents lacking an explicit
            # sign default to positive, this sign is extraneous for purposes
            # of producing human-readable strings from floats.
            r'\+'
            r'|'
            # Non-ignorable negative sign.
            r'(?P<negation>-)'
        r')'
        # Exponent digits.
        #
        # Ignorable zero prefix (optional). For unclear reasons, the "{:g}"
        # format specifier prefixes all exponnet magnitudes in the
        # single-digit range [1, 9] with a zero, which is extraneous for
        # purposes of producing human-readable strings from floats.
        r'0?'
        # Non-ignorable exponent magnitude.
        r'(?P<magnitude>\d+)'
        # Exponent end.
        r'$'
    )

# ....................{ CONVERTERS                         }....................
@type_check
def to_str(number: float) -> str:
    '''
    Human-readable string losslessly converted from the passed floating point
    number.

    This function effectively pretty-prints floats, reducing the unnecessarily
    verbose strings produced by the ``{:g}`` format specifier as follows:

    * The extraneous positive sign preceding positive exponents is removed
      (e.g., reducing ``6.66e+77`` to simply ``6.66e77``).
    * The extraneous zero preceding single-digit exponents is removed (e.g.,
      reducing ``6.66e-07`` to simply ``6.66e-7``).

    Parameters
    ----------
    number : float
        Floating point number to be stringified.

    Returns
    ----------
    str
        Human-readable string losslessly converted from this number.

    See Also
    ----------
    https://jdreaver.com/posts/2014-07-28-scientific-notation-spin-box-pyside.html
        Blog article partially inspiring this implementation.

    Examples
    ----------
        >>> from betse.util.type.numeric import floats
        >>> print(floats.to_str(6.66e7))
        6.66e7
        >>> print('{:g}'.format(6.66e7))
        6.66e+07
    '''

    # Avoid circular import dependencies.
    from betse.util.type.text import regexes

    # Mostly human-readable string losslessly converted from this number.
    number_str = '{:g}'.format(number)

    # Improve this string's readability by removing all extraneous syntax.
    number_str = regexes.replace_substrs(
        text=number_str,
        regex=_get_float_exponent_regex(),

        # Callable passed the object matching the exponent of this floating
        # point number if any. Ideally, a raw string resembling the following
        # would be passed:
        #
        #     replacement=r'e\g<negation>\g<magnitude>',
        #
        # In Python 3.6, this would be feasible. In prior versions of Python,
        # however, this is infeasible. Why? Whereas Python 3.6 expands unmatched
        # backreferences to the empty string, Python < 3.6 expands unmatched
        # backreferences to None, raising the following exception:
        #
        #     sre_constants.error: unmatched group
        replacement=lambda match:
            'e' +
            (match.group('negation') or '') +
            match.group('magnitude')
    )

    # Return this string.
    return number_str