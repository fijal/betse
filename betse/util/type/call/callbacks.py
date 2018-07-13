#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright 2014-2018 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Low-level **callback** (i.e., caller-defined object external to this
application whose methods are called by other methods internal to this
application as a means of facilitating inter-package communication)
functionality.
'''

# ....................{ IMPORTS                           }....................
from abc import ABCMeta  #, abstractmethod
from betse.exceptions import BetseCallbackException
# from betse.util.io.log import logs
from betse.util.type.types import type_check  #, NoneType

# ....................{ SUPERCLASSES                      }....................
class CallbacksABC(metaclass=ABCMeta):
    '''
    Abstract base class of all **callbacks** (i.e., caller-defined object
    external to this application whose methods are called by other methods
    internal to this application as a means of facilitating inter-package
    communication) subclasses.

    Each of the public methods defined by this superclass is a callback
    intended to be called *only* by the **source callable** (i.e., function or
    method calling each such callback), which receives this object from the
    **sink callable** (i.e., function or method instantiating this object and
    passing this object to the source callable).

    Attributes
    ----------
    _progress_min : int
        Minimum value passed to the most recent call to the
        :meth:`progress_ranged` callback by the source callable. While commonly
        0, the sink callable should *not* assume this to be the case.
    _progress_max : int
        Maximum value passed to the most recent call to the
        :meth:`progress_ranged` callback by the source callable.
    _progress_next : int
        Next value to be implicitly passed to the next call to the
        :meth:`progressed` callback by the :meth:`progressed_next` callback.
    '''

    # ..................{ INITIALIZERS                      }..................
    def __init__(self) -> None:
        '''
        Initialize this callbacks object.
        '''

        # Nullify all instance variables for safety.
        self._clear_progress()

    # ..................{ CALLBACKS ~ progress              }..................
    @type_check
    def progress_ranged(
        self, progress_max: int, progress_min: int = 0) -> None:
        '''
        Callback passed the range of progress values subsequently passed to the
        :meth:`progressed` callback by the source callable.

        Design
        ----------
        The source callable should explicitly call the following callbacks
        *before* performing significant work (in order):

        #. This callback exactly once. Doing so enables the sink callable to
           configure external objects (e.g., progress bars) requiring this
           range.
        #. Either:

           * The :meth:`progressed_next` callback. (Recommended.)
           * The :meth:`progressed` callback with the minimum progress value
             passed to this callback. Since doing so is equivalent to calling
             the :meth:`progressed_next` callback, calling the latter comes
             recommended.

        In either case, the call to the second such callback initializes the
        same external objects (e.g., progress bars) to the minimum progress of
        this range. By design, this :meth:`progress_ranged` callback does *not*
        implicitly call either the :meth:`progressed` or
        :meth:`progressed_next` callbacks on your behalf. Doing so would invite
        chicken-and-egg subtleties with subclasses overriding this method to
        configure external objects.

        Subclasses are required to reimplement this callback and call this
        superclass implementation in their own reimplementation.

        Parameters
        ----------
        progress_min : optional[int]
            Minimum value subsequently passed to the :meth:`progressed`
            callback by the source callable. Defaults to 0, ensuring the
            ``progress_max`` parameter to be exactly equal to the number of
            times that the :meth:`progressed_next` callback is called by the
            source callable. Nonetheless, the sink callable should *not* assume
            this value to always be 0.
        progress_max : int
            Maximum value subsequently passed to the :meth:`progressed`
            callback by the source callable. If the ``progress_min`` parameter
            is 0, this is equivalent to the number of times that the
            :meth:`progressed_next` callback is called by the source callable.

        Raises
        ----------
        :class:`BetseCallbackException`
            If either:

            * The source callable is still performing work (i.e., the
              :meth:`progressed` callback has yet to be called with a progress
              value equal to ``progress_max``).
            * ``progress_min`` is greater than or equal to ``progress_max``.
        '''

        # If this range is invalid, raise an exception.
        if progress_min > progress_max:
            raise BetseCallbackException(
                'Minimum progress {} exceeds maximum progress {}.'.format(
                    progress_min, progress_max))
        elif progress_min == progress_max:
            raise BetseCallbackException(
                'Minimum progress {} equals maximum progress {}.'.format(
                    progress_min, progress_max))

        # If the source callable is still performing work, raise an exception.
        self._die_if_progressing()

        # Classify all passed parameters for subsequent reference by the
        # progressed() callback.
        self._progress_min = progress_min
        self._progress_max = progress_max

        # Value to be subsequently passed to the progressed() callback by the
        # first call to the progressed_next() callback. See the
        # progressed_next() callback for a justification of the "+ 1" here.
        self._progress_next = progress_min + 1
        # logs.log_debug('next progress: %d', self._progress_next)


    @type_check
    def progressed(self, progress: int) -> None:
        '''
        Callback passed the current state of progress for work performed by the
        source callable.

        If this is the last possible progress value (i.e., if the passed
        ``progress`` parameter is equal to the ``progress_max`` parameter
        previously passed to the :meth:`progress_ranged` callback), this method
        additionally records the source callable to no longer be performing
        work by calling the :meth:`_clear_progress` method. This preserves
        contractual guarantees, including the guarantee that the next call to
        either this or the :meth:`progressed_next` callback will raise an
        exception.

        Design
        ----------
        The source callable should call this callback repeatedly while
        performing any significant work. Doing so enables the sink callable to
        incrementally update external objects (e.g., progress bars).

        Subclasses are required to reimplement this callback and call this
        superclass implementation in their own reimplementation.

        Parameters
        ----------
        progress : int
            Current state of progress for work performed by the source
            callable. If this integer is *not* in the range previously passed
            to the :meth:`progress_ranged` callback, an exception is raised. If
            this is the first call to this callback by the source callable,
            this integer should ideally be one larger than the minimum progress
            value previously passed to the :meth:`progress_ranged` callback.
            See the :meth:`progressed_next` callback for further discussion.

        Raises
        ----------
        :class:`BetseCallbackException`
            If either:

            * The :meth:`progress_ranged` callback has yet to be called.
            * This progress is *not* in the range previously passed to the
              :meth:`progress_ranged` callback by this source callable.

        See Also
        ----------
        :meth:`progressed_first`
        :meth:`progressed_next`
        :meth:`progressed_last`
            Higher-level callbacks automatically passing the next progress
            value according to the the range previously passed to the
            :meth:`progress_ranged` callback.
        '''

        # If progress_ranged() has yet to be called, raise an exception.
        self._die_unless_progressing()

        # If this progress is *NOT* in the range previously passed to
        # progress_ranged(), raise an exception.
        if not (self._progress_min <= progress <= self._progress_max):
            raise BetseCallbackException(
                'Progress {} not in range [{}, {}].'.format(
                    progress, self._progress_min, self._progress_max))

        # If this is the last possible progress value, record the source
        # callable to no longer be performing work.
        if progress == self._progress_max:
            self._clear_progress()

    # ..................{ CALLBACKS ~ progress : next       }..................
    def progressed_next(self) -> None:
        '''
        Higher-level callback wrapping the lower-level :meth:`progressed`
        callback by automatically passing the next progress value to that
        callback according to the range previously passed to the
        :meth:`progress_ranged` callback.

        Note that callers recalling this callback a predetermined number of
        times are advised to replace the first and last calls to this callback
        with calls to the higher-level :meth:`progressed_first` and
        :meth:`progressed_last` callbacks. Doing so ensures that the first and
        last progress values passed to the sink callable are the minimum and
        maximum progress values previously passed to the
        :meth:`progress_ranged` callback (respectively).

        Guarantees
        ----------
        The first call to this callback is guaranteed to emit one greater than
        the minimum progress value previously passed to the
        :meth:`progress_ranged` callback. While arguably unintuitive, this
        behaviour corresponds with expectations in the sink callable.

        Assuming that the minimum progress value previously passed to the
        :meth:`progress_ranged` callback was 0 as is the common case, this
        behaviour has the additional advantage of guaranteeing that the maximum
        progress value previously passed to that callback is exactly equal to
        the number of times that this :meth:`progressed_next` callback is
        called by the source callable.

        Specifically, since the sink callable typically handles the
        :meth:`progress_ranged` callback by configuring a progress bar to the
        passed range, the sink callable is assumed to have already "consumed"
        the first progress value for all intents and purposes; instructing the
        sink callable to "reconsume" the same progress value would effectively
        hide the actual first iteration of work performed by the source
        callable from the end user perspective.

        Design
        ----------
        For generality, the sink callable should typically *only* handle the
        :meth:`progressed` callback. This callback is merely syntactic sugar
        conveniently simplifying the implementation of the source callback
        calling this callback.

        Raises
        ----------
        :class:`BetseCallbackException`
            If the :meth:`progress_ranged` callback has yet to be called.
        '''

        # If progress_ranged() has yet to be called, raise an exception.
        self._die_unless_progressing()

        # Notify the sink callback of the current state of progress.
        self.progressed(progress=self._progress_next)

        # If the source callback has work remaining to perform, increment this
        # state *AFTER* notifying this callback.
        if self._progress_next is not None:
            self._progress_next += 1


    #FIXME: Excise all references to this method, which rather now appears to
    #be a poor idea.
    # def progressed_first(self) -> None:
    #     '''
    #     Higher-level callback wrapping the lower-level :meth:`progressed_next`
    #     callback by internally calling that callback and raising an exception
    #     if the current progress value is *not* the maximum progress value
    #     previously passed to the :meth:`progress_ranged` callback.
    #
    #     This callback is intended to be called by callers recalling the
    #     :meth:`progressed_next` callback a predetermined number of times as a
    #     replacement for the last such call. Doing so ensures that the last
    #     progress value passed to the sink callable is the maximum.
    #
    #     Raises
    #     ----------
    #     :class:`BetseCallbackException`
    #         If either:
    #
    #         * The :meth:`progress_ranged` callback has yet to be called.
    #         * The current progress value is *not* the maximum progress value.
    #     '''
    #
    #     # If progress_ranged() has yet to be called, raise an exception.
    #     self._die_unless_progressing()
    #
    #     # Notify the sink callback of the initial state of progress.
    #     self.progressed(progress=self._progress_min)


    def progressed_last(self) -> None:
        '''
        Higher-level callback wrapping the lower-level :meth:`progressed_next`
        callback by internally calling that callback and raising an exception
        if the current progress value is *not* the maximum progress value
        previously passed to the :meth:`progress_ranged` callback.

        This callback is intended to be called by callers recalling the
        :meth:`progressed_next` callback a predetermined number of times as a
        replacement for the last such call. Doing so ensures that the last
        progress value passed to the sink callable is the maximum.

        Raises
        ----------
        :class:`BetseCallbackException`
            If either:

            * The :meth:`progress_ranged` callback has yet to be called.
            * The current progress value is *not* the maximum progress value.
        '''

        # Notify the sink callback of the current state of progress.
        self.progressed_next()

        # If the source callable is still performing work, raise an exception.
        self._die_if_progressing()

    # ..................{ EXCEPTIONS                        }..................
    def _die_if_progressing(self) -> None:
        '''
        Raise an exception if the source callable is still performing work.

        Raises
        ----------
        :class:`BetseCallbackException`
            If the source callable is currently performing work.

        See Also
        ----------
        :meth:`_is_progressing`
            Further details.
        '''

        if self._is_progressing:
            raise BetseCallbackException(
                'progress_ranged() callback called before '
                'progressed() callback called with maximum progress value.')


    def _die_unless_progressing(self) -> None:
        '''
        Raise an exception unless the source callable is still performing work.

        Raises
        ----------
        :class:`BetseCallbackException`
            If the source callable is *not* currently performing work.

        See Also
        ----------
        :meth:`_is_progressing`
            Further details.
        '''

        if not self._is_progressing:
            raise BetseCallbackException(
                'progressed() callback called before '
                'progress_ranged() callback.')

    # ..................{ TESTERS                           }..................
    @property
    def _is_progressing(self) -> bool:
        '''
        ``True`` only if the source callable is still performing work.

        Equivalently, this method returns ``False`` only:

        * If the source callable is *not* currently performing work.
        * If the state of work performed by this callable has been cleared
          (i.e., to ``None`` values) rather than set to non-``None`` integers.
        * Unless the :meth:`progress_ranged` callback has been called more
          recently than the :meth:`_clear_progress` method.
        '''

        return (
            self._progress_min  is not None and
            self._progress_max  is not None and
            self._progress_next is not None
        )

    # ..................{ CLEARERS                          }..................
    def _clear_progress(self) -> None:
        '''
        Record the source callable to no longer be performing work by clearing
        (i.e., resetting) the state of work performed by this callable to
        ``None`` values.
        '''

        # Nullify all instance variables for safety.
        self._progress_min = None
        self._progress_max = None
        self._progress_next = None
