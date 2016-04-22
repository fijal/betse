#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''
Low-level logging configuration.

Logging Levels
----------
Logging levels are integer-comparable according to the standard semantics of
the `<` comparator. Levels assigned smaller integers are more inclusive (i.e.,
log strictly more messages than) levels assigned larger integers: e.g.,

    # "DEBUG" is less than and hence more inclusive than "INFO".
    >>> logging.DEBUG < logging.INFO
    True

'''

# ....................{ IMPORTS                            }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: To avoid circular import dependencies, import only modules *NOT*
# importing this module at the top-level. Currently, the following modules
# import this module at the top-level and hence *CANNOT* be imported here:
# "betse.util.os.processes".
#
# Since all other modules should *ALWAYS* be able to safely import this module
# at any level, such circularities are best avoided here rather than elsewhere.
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

import logging, os, sys
from betse.exceptions import BetseExceptionFile
from betse.util.type import types
from collections import OrderedDict
from enum import Enum
from logging import Filter, Formatter, LogRecord, StreamHandler
from logging.handlers import RotatingFileHandler
from os import path

# ....................{ CONSTANTS ~ int                    }....................
# Originally, we attempted to dynamically copy such constants from the "logging"
# to the current module. Such attempts succeeded in exposing such constants to
# other modules importing this module but *NOT* to this module itself. Hence,
# such constants are manually copied.

DEBUG = logging.DEBUG
'''
Logging level suitable for debugging messages.
'''

INFO = logging.INFO
'''
Logging level suitable for informational messages.
'''

WARNING = logging.WARNING
'''
Logging level suitable for warning messages.
'''

ERROR = logging.ERROR
'''
Logging level suitable for error messages.
'''

CRITICAL = logging.CRITICAL
'''
Logging level suitable for critical messages.
'''

NONE = logging.CRITICAL + 1024
'''
Logging level signifying no messages to be logged.

Since the `logging` module defines no constants encapsulating the concept of
"none" (that is, of logging nothing), this is an ad-hoc constant expected to be
larger than the largest constant defined by that module.
'''

ALL = logging.NOTSET
'''
Logging level signifying all messages to be logged.

Since the `logging` module defines no constants encapsulating the concept of
"all" (that is, of logging everything), this is an ad-hoc constant expected to
be smaller than the smallest constant defined by that module.
'''

# ....................{ ENUMERATIONS                       }....................
LogType = Enum('LogType', ('NONE', 'FILE'))
'''
Enumeration of all possible types of logging to perform, corresponding exactly
to the `--log-type` CLI option.

Attributes
----------
none : enum
    Enumeration member redirecting all logging to standard file handles, in
    which case:
    * All `INFO` and `DEBUG` log messages will be printed to stdout.
    * All `ERROR` and `WARNING` log messages will be printed to stderr.
    * All uncaught exceptions will be printed to stderr.
file : enum
    Enumeration member redirecting all logging to the current logfile.
'''

# ....................{ GETTERS                            }....................
def get_metadata() -> OrderedDict:
    '''
    Get an ordered dictionary synopsizing the current logging configuration.
    '''

    return OrderedDict((
        ('type', log_config.log_type.name.lower()),
        ('file', log_config.filename),
        ('verbose', str(log_config.is_verbose).lower()),
    ))

# ....................{ CONFIG                             }....................
#FIXME: Update docstring to reflect the new default configuration.
class LogConfig(object):
    '''
    Default logging configuration.

    Such configuration defines sensible default handlers for the root logger,
    which callers may customize (e.g., according to user-defined settings) by
    calling the appropriate getters.

    Caveats
    ----------
    Since this class' `__init__()` method may raise exceptions, this class
    should be instantiated at application startup _after_ establishing default
    exception handling.

    Default Settings
    ----------
    All loggers will implicitly propagate messages to the root logger configured
    by this class, whose output will be:

    * Formatted in a timestamped manner detailing the point of origin (e.g.,
      "[2016-04-03 22:02:47] betse ERROR (util.py:50): File not found.").
    * Labelled as the current logger's name, defaulting to `root`. Since this
      is _not_ a terribly descriptive name, callers are encouraged to
    * Printed to standard error if the logging level for this output is either
      `WARNING`, `ERROR`, or `CRITICAL`.
    * Printed to standard output if the logging level for this output is
      `INFO`. Together with the prior item, this suggests that output with a
      logging level of `DEBUG` will _not_ be printed by default.
    * Appended to the user-specific file given by
      `pathtree.LOG_DEFAULT_FILENAME`, whose:
      * Level defaults to `logger.ALL`. Hence, _all_ messages will be logged by
        default, including low-level debug messages. (This is helpful for
        debugging client-side errors.)
      * Contents will be automatically rotated on exceeding a sensible filesize
        (e.g., 16Kb).

    If the default log levels are undesirable, consider subsequently calling
    such logger's `set_level()` method. Since a desired log level is typically
    unavailable until *after* parsing CLI arguments and/or configuration file
    settings *AND* since a logger is required before such level becomes
    available, this function assumes a sane interim default.

    Attributes
    ----------
    _logger_root_handler_file : Handler
        Root logger handler appending to the current logfile if any _or_ `None`
        otherwise.
    _logger_root_handler_stderr : Handler
        Root logger handler printing to standard error.
    _logger_root_handler_stdout : Handler
        Root logger handler printing to standard output.
    _filename : str
        Absolute or relative path of the file logged to by the file handler.
    _log_type : LogType
        Type of logging to be performed.
    _logger_root : Logger
        Root logger.
    '''

    # ..................{ INITIALIZERS                       }..................
    def __init__(self):
        '''
        Initialize this logging configuration as documented by the class
        docstring.
        '''

        # Initialize the superclass.
        super().__init__()

        # Initialize all non-property attributes to sane defaults. To avoid
        # chicken-and-egg issues, properties should *NOT* be set here.
        self._logger_root_handler_file = None
        self._logger_root_handler_stderr = None
        self._logger_root_handler_stdout = None
        self._filename = None
        self._log_type = LogType.NONE
        self._logger_root = None

        # Initialize the root logger and all root logger handlers for logging.
        self._init_logging()


    def _init_logging(self) -> None:
        '''
        Initialize the root logger _and_ all root logger handlers.
        '''

        # Initialize root logger handlers.
        self._init_logger_root_handlers()

        # Initialize the root logger *AFTER* handlers.
        self._init_logger_root()

        # Redirect all warnings through the logging framewark *AFTER*
        # successfully performing the above initialization.
        logging.captureWarnings(True)


    def _init_logger_root_handlers(self) -> None:
        '''
        Initialize root logger handlers.
        '''

        # Avoid circular import dependencies.
        from betse.util.os import processes

        # Initialize the stdout handler.
        #
        # Sadly, the "StreamHandler" constructor does *NOT* accept the customary
        # "level" attribute accepted by its superclass constructor.
        self._logger_root_handler_stdout = StreamHandler(sys.stdout)
        self._logger_root_handler_stdout.setLevel(INFO)
        self._logger_root_handler_stdout.addFilter(LoggerFilterInfoOrLess())

        # Initialize the stderr handler.
        self._logger_root_handler_stderr = StreamHandler(sys.stderr)
        self._logger_root_handler_stderr.setLevel(WARNING)

        # Initialize the file handler... to nothing. This handler will be
        # initialized to an actual instance on the "type" property being set to
        # "LogType.FILE" by an external caller.
        self._logger_root_handler_file = None

        #FIXME: Consider colourizing this format string.

        # Format standard output and error in the conventional way. For a list
        # of all available log record attributes, see:
        #
        #     https://docs.python.org/3/library/logging.html#logrecord-attributes
        #
        # Note that the "processName" attribute appears to *ALWAYS* expand to
        # "MainProcess", which is not terribly descriptive. Hence, the name of
        # the current process is manually embedded in such format.
        #
        # Note that "{{" and "}}" substrings in format() strings escape literal
        # "{" and "}" characters, respectively.
        stream_format = '[{}] {{message}}'.format(
            processes.get_current_basename())

        # Formatters for these formats.
        stream_formatter = LoggerFormatterStream(stream_format, style='{')

        # Assign these formatters to these handlers.
        self._logger_root_handler_stdout.setFormatter(stream_formatter)
        self._logger_root_handler_stderr.setFormatter(stream_formatter)


    def _init_logger_root_handler_file(self) -> None:
        '''
        Reconfigure the file handler to log to the log filename if desired.

        If file logging is disabled (i.e., the current log type is _not_
        `LogType.FILE`), this method reduces to a noop. If no log filename is
        defined (i.e., the `filename` property has _not_ been explicitly set by
        an external caller), an exception is raised.

        Otherwise, this method necessarily destroys the existing file handler if
        any and creates a new file handler. Why? Because file handlers are _not_
        safely reconfigurable as is.
        '''

        # Avoid circular import dependencies.
        from betse.util.os import processes
        from betse.util.type import ints

        # Remove the previously registered file handler if any *BEFORE*
        # recreating this handler.
        if self._logger_root_handler_file is not None:
            self._logger_root.removeHandler(self._logger_root_handler_file)

        # If file handling is disabled, noop.
        if not self.is_logging_file:
            return

        # Else, file handling is enabled.
        #
        # If no filename is set, raise an exception.
        if self._filename is None:
            raise BetseExceptionFile('Log filename not set.')

        # Create the directory containing this logfile with standard low-level
        # Python functionality if needed. Since our custom higher-level
        # dirs.make_parent_unless_dir() function logs such creation, calling
        # that function here would induce exceptions in the worst case (due to
        # the root logger having not been fully configured) or subtle errors in
        # the best case.
        os.makedirs(path.dirname(self._filename), exist_ok=True)

        # Root logger file handler, preconfigured as documented above.
        self._logger_root_handler_file = RotatingFileHandler(
            filename=self._filename,

            # Append rather than overwrite this file.
            mode='a',

            # Encode such file's contents as UTF-8.
            encoding='utf-8',

            # Filesize at which to rotate this file.
            maxBytes=32 * ints.KB,

            # Maximum number of rotated logfiles to maintain.
            backupCount=8,
        )
        self._logger_root_handler_file.setLevel(ALL)

        # Linux-style logfile format.
        file_format = (
            '[{{asctime}}] {} {{levelname}} '
            '({{module}}.py:{{funcName}}():{{lineno}}):\n'
            '    {{message}}'.format(processes.get_current_basename()))

        # Format this file according to this format.
        file_formatter = LoggerFormatterStream(file_format, style='{')
        self._logger_root_handler_file.setFormatter(file_formatter)

        # Register this handler with the root logger *AFTER* successfully
        # configuring this handler.
        self._logger_root.addHandler(self._logger_root_handler_file)


    def _init_logger_root(self) -> None:
        '''
        Initialize the root logger with all previously initialized handlers.
        '''

        # Root logger.
        self._logger_root = logging.getLogger()

        # Instruct this logger to entertain all log requests, ensuring these
        # requests will be delegated to the handlers defined below. By default,
        # this logger ignores all log requests with level less than "WARNING",
        # preventing handlers from receiving these requests.
        self._logger_root.setLevel(ALL)

        # Register all initialized handlers with the root logger *AFTER*
        # successfully configuring these handlers. Since the file handler is
        # subsequently initialized, defer adding that handler.
        self._logger_root.addHandler(self._logger_root_handler_stdout)
        self._logger_root.addHandler(self._logger_root_handler_stderr)

    # ..................{ PROPERTIES ~ bool                  }..................
    @property
    def is_logging_file(self) -> bool:
        '''
        `True` only if file logging is enabled (i.e., if the `log_type` property
        is `LogType.FILE`).
        '''
        return self.log_type is LogType.FILE

    # ..................{ PROPERTIES ~ bool : verbose        }..................
    #FIXME: Define a corresponding setter.
    @property
    def is_verbose(self) -> bool:
        '''
        `True` only if _all_ messages are to be unconditionally logged to the
        stdout Handler (and hence printed to stdout).

        Equivalently, this method returns `True` only if the logging level for
        the stdout handler is `ALL`.
        '''

        return self._logger_root_handler_stdout.level == ALL


    @is_verbose.setter
    def is_verbose(self, is_verbose: bool) -> None:
        '''
        Set the verbosity of the stdout handler.

        This method sets the logging level for the stdout handler to:

        * `ALL` if the passed boolean is `True`.
        * `INFO` if the passed boolean is `False`.
        '''
        assert types.is_bool(is_verbose), types.assert_not_bool(is_verbose)

        # Convert the passed boolean to a logging level for the stdout handler.
        if is_verbose:
            self._logger_root_handler_stdout.setLevel(ALL)
        else:
            self._logger_root_handler_stdout.setLevel(INFO)

    # ..................{ PROPERTIES ~ type                  }..................
    @property
    def log_type(self) -> LogType:
        '''
        Type of logging to be performed.
        '''

        return self._log_type


    @log_type.setter
    def log_type(self, log_type: LogType) -> None:
        '''
        Set the type of logging to be performed.

        If file logging is enabled (i.e., the passed log type is `FILE`):

        * If no log filename is defined (i.e., the `filename` property has _not_
          been explicitly set by an external caller), an exception is raised.
        * Else, the file handler is reconfigured to log to that file.
        '''
        assert types.is_in_enum(log_type, LogType), (
            types.assert_not_in_enum(log_type, LogType))

        # Record this log_type *BEFORE* reconfiguring loggers or handlers, which
        # access this private attribute through its public property.
        self._log_type = log_type

        # Reconfigure the file handler if needed.
        self._init_logger_root_handler_file()

    # ..................{ PROPERTIES ~ path                  }..................
    @property
    def filename(self) -> str:
        '''
        Absolute or relative path of the file logged to by the file handler.
        '''

        return self._filename


    @filename.setter
    def filename(self, filename: str) -> None:
        '''
        Set the absolute or relative path of the file logged to by the file
        handler.

        If file logging is enabled (i.e., the current log type is
        `LogType.FILE`), this method reconfigures the file handler accordingly;
        else, this filename is effectively ignored.
        '''
        assert types.is_str_nonempty(filename), (
            types.assert_not_str_nonempty(filename, 'Log filename'))

        # Record this filename *BEFORE* reconfiguring the file handler, which
        # accesses this private attribute through its public property.
        self._filename = filename

        # Reconfigure the file handler if needed.
        self._init_logger_root_handler_file()

    # ..................{ PROPERTIES ~ handler               }..................
    # Read-only properties prohibiting write access to external callers.

    @property
    def handler_file(self) -> logging.Handler:
        '''
        Root logger handler appending to the current logfile if file logging is
        enabled _or_ `None` otherwise.
        '''
        return self._logger_root_handler_file


    @property
    def handler_stderr(self) -> logging.Handler:
        '''
        Root logger handler printing to standard error.
        '''
        return self._logger_root_handler_stderr


    @property
    def handler_stdout(self) -> logging.Handler:
        '''
        Root logger handler printing to standard output.
        '''
        return self._logger_root_handler_stdout

# ....................{ CLASSES ~ filter                   }....................
class LoggerFilterInfoOrLess(Filter):
    '''
    Filter ignoring log records with logging level larger than `INFO`.

    This filter retains only log records with logging level of `INFO` or less.
    '''

    def filter(self, log_record: LogRecord) -> str:
        '''
        `True` only if the passed log record has a logging level of `INFO` or
        less.
        '''
        assert isinstance(log_record, LogRecord), (
            '"{}" not a log record.'.format(log_record))

        return log_record.levelno <= INFO

# ....................{ CLASSES ~ formatter                }....................
#FIXME: Unfortunately, this fundamentally fails to work. The reason why? The
#"TextWrapper" class inserts spurious newlines *EVEN WHEN YOU EXPLICITLY TELL
#IT NOT TO*. This is crazy, but noted in the documentation:
#
#    "If replace_whitespace is False, newlines may appear in the middle of a
#     line and cause strange output. For this reason, text should be split into
#     paragraphs (using str.splitlines() or similar) which are wrapped
#     separately."
#
#Until this is resolved, the only remaining means of wrapping log messages will
#be to define new top-level module functions suffixed by "_wrapped" ensuring
#that the appropriate formatter is used (e.g., a new log_info_wrapped()
#function). For now, let's just avoid the topic entirely. It's all a bit
#cumbersome and we're rather weary of it.

class LoggerFormatterStream(Formatter):
    '''
    Formatter wrapping lines in log messages to the default line length.

    Attributes
    ----------
    _text_wrapper : TextWrapper
        Object with which to wrap log messages, cached for efficiency.
    '''
    pass
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self._text_wrapper = TextWrapper(
    #         drop_whitespace = False,
    #         replace_whitespace = False,
    #     )

    # def format(self, log_record: LogRecord) -> str:
    #     # Avoid circular import dependencies.
    #     from betse.util.type import strs
    #
    #     # Get such message by (in order):
    #     #
    #     # * Formatting such message according to our superclass.
    #     # * Wrapping such formatted message.
    #     return strs.wrap(
    #         text = super().format(log_record),
    #         text_wrapper = self._text_wrapper,
    #     )

# ....................{ SINGLETON                          }....................
log_config = LogConfig()
'''
Singleton logging configuration.

This configuration provides access to root logger handlers. In particular, this
simplifies modification of logging levels at runtime (e.g., in response to
command-line arguments or configuration file settings).
'''