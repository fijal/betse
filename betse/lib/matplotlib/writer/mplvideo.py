#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Matplotlib-specific classes writing animations as video.
'''

#FIXME: Consider contributing most or all of this submodule back to matplotlib.

# ....................{ IMPORTS                            }....................
from betse.exceptions import BetseMatplotlibException
from betse.util.io.log import logs
from betse.util.path.command import pathables, runners
from betse.util.type import regexes, strs
from betse.util.type.mappings import bidict
from betse.util.type.types import type_check, NoneType, SequenceTypes
from matplotlib.animation import writers

# ....................{ DICTS                              }....................
WRITER_NAME_TO_COMMAND_BASENAME = bidict(
    # AVConv-based video encoding with pipe-based writing.
    avconv='avconv',

    # AVConv-based video encoding with file-based writing.
    avconv_file='avconv',

    # FFmpeg-based video encoding with pipe-based writing.
    ffmpeg='ffmpeg',

    # FFmpeg-based video encoding with file-based writing.
    ffmpeg_file='ffmpeg',

    # Mencoder-based video encoding with pipe-based writing.
    mencoder='mencoder',

    # Mencoder-based video encoding with file-based writing.
    mencoder_file='mencoder',

    # ImageMagick-based animated GIF encoding with pipe-based writing.
    imagemagick='convert',

    # ImageMagick-based animated GIF encoding with file-based writing.
    imagemagick_file='convert',
)
'''
Bidirectional dictionary mapping the matplotlib-specific name of each video
encoder supported by matplotlib (e.g., `imagemagick`) to and from the basename
of that encoder's external command (e.g., `convert`).

These mappings are accessible as follows:

* `WRITER_NAME_TO_COMMAND_BASENAME`, the forward mapping from encoder names to
  command basenames.
* `WRITER_NAME_TO_COMMAND_BASENAME.reverse`, the reverse mapping from command
  basenames to encoder names.
'''


# Subsequently initialized by the init() function.
WRITER_BASENAME_TO_CONTAINER_FILETYPE_TO_CODEC_NAMES = None
'''
Dictionary mapping from the basename of the external command for each video
encoder recognized by matplotlib (e.g., `ffmpeg`) to a nested dictionary mapping
from the filetype of each video container format recognized by BETSE (e.g.,
`mp4`) to a list of the names of all widely used video codecs supported by that
encoder (in descending order of general-purpose, subjective preference).

Since multiple matplotlib animation writers (e.g., `ffmpeg`, `ffmpeg_file`)
typically execute the same external command (e.g., `ffmpeg`), this dictionary
maps from the latter rather than the former. Mapping from the former would
needlessly require redundant mappings for writers sharing the same command.

This dictionary is principally used by the `get_first_codec_name()` utility
function to obtain the preferred codec for a given combination of video
encoder and container format.
'''

# ....................{ INITIALIZERS                       }....................
# For simplicity, this function is called below on the first importation of this
# submodule rather than explicitly called by callers.
def init() -> None:
    '''
    Initialize all global variables declared by this submodule.
    '''

    # Globals initialized below.
    global WRITER_BASENAME_TO_CONTAINER_FILETYPE_TO_CODEC_NAMES

    WRITER_BASENAME_TO_CONTAINER_FILETYPE_TO_CODEC_NAMES = {
        # FFmpeg.
        'ffmpeg': {
            # Audio Video Interleave (AVI). AVI supports the smallest subset of
            # MPEG-centric codecs of all recognized container formats and hence
            # serves as the baseline for listing such codecs.
            'avi': [
                # H.264 / AVC / MPEG-4 Part 10.
                'libx264',
                # MPEG-4 Part 2 Advanced Simple Profile (ASP) via an external
                # shared library, typically providing better quality at lower
                # bitrates than the otherwise equivalent built-in codec for
                # MPEG-4 Part 2 (i.e., "mpeg4").
                'libxvid',
                # MPEG-4 Part 2 Advanced Simple Profile (ASP) support built-in
                # to all FFmpeg installations.
                'mpeg4',
                # H.263. Assuming videos leveraging this codec to be encoded as
                # basic "baseline" H.263 bitstreams, these videos are decodable
                # as is by conventional MPEG-4 decoders. To quote the eponymous
                # Wikipedia article on H.263: "MPEG-4 Part 2 is H.263 compatible
                # in the sense that basic 'baseline' H.263 bitstreams are
                # correctly decoded by an MPEG-4 Video decoder."
                'h263',
                # MPEG-2.
                'mpeg2video',
            ],

            # Graphics Interchange Format (GIF).
            'gif': ['gif'],

            # Matroska.
            'mkv': None,

            # QuickTime.
            'mov': None,

            # MPEG-4 Part 14.
            'mp4': None,

            # Theora.
            'ogv': ['libtheora'],

            # WebM.
            'webm': [
                'libvpx-vp9',  # WebM VP-9
                'libvpx',      # WebM VP-8
            ],
        },

        # Libav.
        'avconv': None,

        # Mencoder.
        'mencoder': None,

        # ImageMagick, encoding videos only as old-school animated GIFs. Since
        # ImageMagick is *NOT* a general-purpose video encoder and hence fails
        # to support the notion of video codecs, a codec of "None" is used.
        # This has beneficial side effects, including ensuring that no edge-case
        # functionality in the matplotlib codebase attempts to erroneously
        # encode anything with ImageMagick using a codec.
        'convert': {
            'gif': [None],
        }
    }

    # Shorthand to preserve sanity below.
    codec_names = WRITER_BASENAME_TO_CONTAINER_FILETYPE_TO_CODEC_NAMES

    # For FFmpeg, define the set of all codecs supported by the "mp4" (i.e.,
    # MPEG-4 Part 14) and "mov" (i.e., QuickTime) container formats to be the
    # same superset of those supported by the now-obsolete AVI container format.
    codec_names['ffmpeg']['mp4'] = codec_names['ffmpeg']['avi'] + [
        # H.265 / HEVC / MPEG-H Part 2.
        'hevc',
    ]
    codec_names['ffmpeg']['mov'] = codec_names['ffmpeg']['mp4']

    # For FFmpeg, define the set of all codecs supported by the "mkv" (i.e.,
    # Matroska) container format to the set of all codecs supported by all other
    # container formats, excluding animated GIFs. Matroska: it doth rocketh.
    codec_names['ffmpeg']['mkv'] = (
        codec_names['ffmpeg']['mp4'] +
        codec_names['ffmpeg']['ogv'] +
        codec_names['ffmpeg']['webm']
    )

    # Define Libav to support exactly all codecs supported by FFmpeg. Since the
    # two are well-synchronized forks of each other attempting (and mostly
    # succeeding) to preserve a common command-line API, assuming codec parity
    # is typically a safe assumption.
    codec_names['avconv'] = ['ffmpeg']

    # Define Mencoder to support exactly all codecs supported by FFmpeg. Since
    # Mencoder internally leverages the same "libavcodec" shared library
    # leveraged by FFmpeg, assuming codec parity is *ALWAYS* a safe assumption.
    # While Mencoder also provides a small handful of Mencoder-specific codecs
    # (see "mencoder -ovc help"), these codecs are commonly regarded as inferior
    # to their "libavcodec" counterparts. In either case, matplotlib internally
    # mandates use of "libavcodec"-provided codecs rather than Mencoder-specific
    # codecs in all Mencoder writer classes (e.g., "MencoderWriter").
    codec_names['mencoder'] = ['ffmpeg']

# ....................{ EXCEPTIONS                         }....................
def die_unless_writer(writer_name: str) -> None:
    '''
    Raise an exception unless a video encoder with the passed
    matplotlib-specific name is recognized by both matplotlib and BETSE itself.

    Parameters
    ----------
    writer_name : str
        Matplotlib-specific alphanumeric lowercase name of the encoder to test.

    See Also
    ----------
    is_writer
        Further details.
    '''

    if not is_writer(writer_name):
        raise BetseMatplotlibException(
            'Matplotlib animation video writer "{}" unrecognized.'.format(
                writer_name))

# ....................{ EXCEPTIONS ~ pathable              }....................
def die_unless_writer_pathable(writer_name: str) -> None:
    '''
    Raise an exception unless a video encoder with the passed
    matplotlib-specific name is recognized by both matplotlib and BETSE itself
    _and_ is an external command in the current `${PATH}`.

    Parameters
    ----------
    writer_name : str
        Matplotlib-specific alphanumeric lowercase name of the encoder to test.

    See Also
    ----------
    is_writer_pathable
        Further details.
    '''

    # If this writer is *NOT* in the ${PATH}...
    if not is_writer_pathable(writer_name):
        # Basename of this writer's command.
        writer_basename = WRITER_NAME_TO_COMMAND_BASENAME[writer_name]

        # Raise an exception.
        raise BetseMatplotlibException(
            'Matplotlib animation video encoder "{}" unrecognized or '
            'not in current ${{PATH}}.'.format(writer_basename))


def die_unless_writer_command_pathable(writer_basename: str) -> None:
    '''
    Raise an exception unless a video encoder whose external command has the
    passed basename is recognized by both matplotlib and BETSE itself _and_ is
    in the current `${PATH}`.

    Parameters
    ----------
    writer_basename : str
        Basename of the external command of the video encoder to test.

    See Also
    ----------
    is_writer_command_pathable
        Further details.
    '''

    if not is_writer_command_pathable(writer_basename):
        raise BetseMatplotlibException(
            'Matplotlib animation video encoder "{}" unrecognized or '
            'not in current ${{PATH}}.'.format(writer_basename))

# ....................{ TESTERS                            }....................
@type_check
def is_writer(writer_name: str) -> bool:
    '''
    `True` only if a video encoder with the passed matplotlib-specific name
    (e.g., `ffmpeg`) is recognized by both matplotlib and BETSE itself.

    Specifically, this function returns `True` only if this name is a key of:

    * The global `matplotlib.animation.writers` dictionary, implying this
      encoder to have registered a matplotlib animation writer class (e.g.,
      `FFmpegWriter`).
    * The global `WRITER_NAME_TO_COMMAND_BASENAME` dictionary of this submodule,
      implying this encoder to be recognized by BETSE itself.

    Parameters
    ----------
    writer_name : str
        Matplotlib-specific alphanumeric lowercase name of the encoder to test.

    Returns
    ----------
    bool
        `True` only if this encoder is recognized by both matplotlib and BETSE.
    '''

    return (
        # "True" only if this encoder is recognized by matplotlib.
        writers.is_available(writer_name) and
        # "True" only if this encoder is recognized by BETSE.
        writer_name in WRITER_NAME_TO_COMMAND_BASENAME
    )


@type_check
def is_writer_basename(writer_basename: str) -> bool:
    '''
    `True` only if a video encoder whose external command has the passed
    basename (e.g., `ffmpeg`) is recognized by both matplotlib and BETSE itself.

    Parameters
    ----------
    writer_basename : str
        Basename of the external command of the video encoder to test.

    Returns
    ----------
    bool
        `True` only if this encoder is recognized by both matplotlib and BETSE.
    '''

    return (
        writer_basename in WRITER_NAME_TO_COMMAND_BASENAME.reverse and
        is_writer(WRITER_NAME_TO_COMMAND_BASENAME.reverse[writer_basename]))

# ....................{ TESTERS ~ pathable                 }....................
@type_check
def is_writer_pathable(writer_name: str) -> bool:
    '''
    `True` only if the video encoder with the passed matplotlib-specific name
    (e.g., `ffmpeg`) is recognized by both matplotlib and BETSE itself _and_ is
    installed as an external command in the current `${PATH}`, typically of the
    same name as the passed name.

    Parameters
    ----------
    writer_name : str
        Matplotlib-specific alphanumeric lowercase name of the encoder to test.

    Returns
    ----------
    bool
        `True` only if the above conditions hold.
    '''

    return is_writer(writer_name) and is_writer_command_pathable(
        WRITER_NAME_TO_COMMAND_BASENAME[writer_name])


@type_check
def is_writer_command_pathable(writer_basename: str) -> bool:
    '''
    `True` only if the video encoder whose external command has the passed
    basename (e.g., `ffmpeg`) is recognized by both matplotlib and BETSE itself
    _and_ is installed as an external command in the current `${PATH}`,
    typically of the same name as the passed name.

    Parameters
    ----------
    writer_basename : str
        Basename of the external command of the video encoder to test.

    Returns
    ----------
    bool
        `True` only if the above conditions hold.
    '''

    return (
        is_writer_basename(writer_basename) and
        pathables.is_pathable(writer_basename))

# ....................{ TESTERS ~ codec                    }....................
@type_check
def is_writer_command_codec(
    writer_basename: str, codec_name: (str, NoneType)) -> bool:
    '''
    `True` only if the video encoder whose external command has the passed
    basename (e.g., `ffmpeg`) supports the video codec with the passed
    encoder-specific name (e.g., `libx264`).

    Specifically, this function returns `True` only if the passed basename is:

    * `ffmpeg` _and_ the `ffmpeg -help encoder={codec_name}` command succeeds.
    * `avconv` _and_ the `avconv -help encoder={codec_name}` command succeeds.
    * `mencoder`, the `mencoder -ovc help` command lists the Mencoder-specific
      `lavc` video codec, _and_ either:
      * `ffmpeg` is in the current `${PATH}` and recursively calling this
        function as `is_writer_codec('ffmpeg', codec_name)` returns `True`.
      * `ffmpeg` is _not_ in the current `${PATH}`, in which case this function
        assumes the passed codec to be supported and simply returns `True`.
    * Any other passed basename (e.g., `convert`, implying ImageMagick) _and_
      the passed codec is `None`. These basenames are assumed to _not_ actually
      be video encoders and thus support _no_ video codecs.

    Parameters
    ----------
    writer_basename : str
        Basename of the external command of the video encoder to test.
    codec_name : str
        Encoder-specific name of the codec to be tested for.

    Returns
    ----------
    bool
        `True` only if this encoder supports this codec.

    Raises
    ----------
    BetseMatplotlibException
        If this basename is either:
        * Unrecognized by matplotlib or BETSE itself.
        * Not found as an external command in the current `${PATH}`.
        * Mencoder and the `mencoder -ovc help` command fails to list the
          Mencoder-specific `lavc` video codec required by Matplotlib.

    See Also
    ----------
    is_writer_pathable
        Tester validating this writer.
    '''

    # If this command is unrecognized or not in the ${PATH}, raise an exception.
    die_unless_writer_command_pathable(writer_basename)

    # For FFmpeg, detect this codec by capturing help documentation output by
    # the "ffmpeg" command for this codec and grepping this output for a string
    # stating this codec to be unrecognized. Sadly, this command reports success
    # rather than failure when this codec is unrecognized. (wut, FFmpeg?)
    if writer_basename == 'ffmpeg':
        # Help documentation for this codec captured from "ffmpeg".
        ffmpeg_codec_help = runners.run_with_stdout_captured(command_words=(
            'ffmpeg', '-help',
            'encoder=' + strs.shell_quote('${codec_name}'.format(codec_name)),
        ))

        # Return whether this documentation is suffixed by a string implying
        # this codec to be unrecognized or not. If this codec is unrecognized,
        # this documentation ends with the following line:
        #
        #     Codec '${codec_name}' is not recognized by FFmpeg.
        return ffmpeg_codec_help.endswith("' is not recognized by FFmpeg.")
    # For Libav, detect this codec in the same exact manner as for FFmpeg.
    elif writer_basename == 'avconv':
        # Help documentation for this codec captured from "avconv".
        avconv_codec_help = runners.run_with_stdout_captured(command_words=(
            'avconv', '-help',
            'encoder=' + strs.shell_quote('${codec_name}'.format(codec_name)),
        ))

        # Return whether this documentation is suffixed by an indicative string.
        return avconv_codec_help.endswith("' is not recognized by Libav.")
    # For Mencoder, detect this codec by capturing help documentation output by
    # the "mencoder" command for *ALL* video codecs, grepping this output for
    # the "lavc" video codec required by matplotlib, and, if found, repeating
    # the above FFmpeg-specific logic to specifically detect this codec.
    elif writer_basename == 'mencoder':
        # Help documentation for all codecs captured from "mencoder".
        mencoder_codecs_help = runners.run_with_stdout_captured(command_words=(
            'mencoder', '-ovc', 'help'))

        # If this output contains a line resembling the following, this
        # installation of Mencoder supports the requisite "lavc" codec:
        #     lavc     - libavcodec codecs - best quality!
        if regexes.is_match(
            text=mencoder_codecs_help,
            regex=r'^\s*lavc\s+',
            flags=regexes.MULTILINE,
        ):
            # If the "ffmpeg" command is in the current ${PATH}, query that
            # command for whether or not the passed codec is supported. Note
            # that the recursion bottoms out with this call, as the above logic
            # handling the FFmpeg writer does *NOT* recall this function.
            if is_writer_pathable('ffmpeg'):
                return is_writer_command_codec('ffmpeg', codec_name)
            # Else, "ffmpeg" is *NOT* in the ${PATH}. Since Mencoder implements
            # "lavc" codec support by linking against the "libavcodec" shared
            # library rather than calling the "ffmpeg" command, it's technically
            # permissible (albeit uncommon) for the "mencoder" but not "ffmpeg"
            # command to be in the ${PATH}. Hence, this does *NOT* indicate a
            # fatal error. This does, however, prevent us from querying whether
            # or not the passed codec is supported. In lieu of sensible
            # alternatives...
            else:
                # Log a non-fatal warning.
                logs.log_warning(
                    'Mencoder "libavcodec"-based video codec "{}" '
                    'possibly unavailable. Consider installing FFmpeg to '
                    'resolve this warning.'.format(codec_name))

                # Assume the passed codec to be supported.
                return True
        # Else, Mencoder fails to support the "lavc" codec. Raise an exception.
        else:
            raise BetseMatplotlibException(
                'Mencoder video codec "lavc" unavailable.')

    # For any other writer (e.g., ImageMagick), assume this writer to *NOT* be
    # a video encoder and hence support *NO* video codecs. In this case, return
    # True only if the passed codec is "None", signifying "no video codec."
    return codec_name is None

# ....................{ GETTERS                            }....................
@type_check
def get_writer_class(writer_name: str) -> type:
    '''
    Get the matplotlib animation writer class (e.g., `ImageMagickWriter`)
    registered with the passed lowercase name (e.g., `imagemagick`).

    Parameters
    ----------
    writer_name : str
        Matplotlib-specific alphanumeric lowercase name of the class to obtain.

    Returns
    ----------
    type
        Matplotlib animation writer class registered with this name.

    Raises
    ----------
    BetseMatplotlibException
        If this writer is unrecognized by either matplotlib or BETSE itself.
    '''

    # If this writer is unrecognized, raise an exception.
    die_unless_writer(writer_name)

    # Return this writer's class.
    return writers[writer_name]

# ....................{ GETTERS ~ first                    }....................
@type_check
def get_first_writer_name(writer_names: SequenceTypes) -> str:
    '''
    Get the first matplotlib-specific name (e.g., `imagemagick`) of the
    matplotlib animation writer class (e.g., `ImageMagickWriter`) in the passed
    list whose corresponding external command (e.g., `convert`) is in the
    current `${PATH}` if any _or_ raise an exception otherwise (i.e., if no such
    writer's command is in the `${PATH}`).

    This function iteratively searches for encoder commands in the same order as
    encoder names are listed in the passed list.

    Parameters
    ----------
    writer_names : SequenceTypes
        List of the matplotlib-specific alphanumeric lowercase names of all
        encoders to search for.

    Returns
    ----------
    str
        Matplotlib-specific name of the first such writer.

    Raises
    ----------
    BetseMatplotlibException
        If either:
        * Any writer in the passed list is unrecognized by matplotlib or BETSE.
        * No such writer's external command is found in the current `${PATH}`.
    '''

    # For the matplotlib-specific name of each passed video encoder...
    for writer_name in writer_names:
        # If this encoder is unrecognized, raise an exception.
        die_unless_writer(writer_name)

        # Basename of this encoder's command.
        writer_basename = WRITER_NAME_TO_COMMAND_BASENAME[writer_name]

        # If this command is in the ${PATH}, cease searching.
        if pathables.is_pathable(writer_basename):
            return writer_name

    # Else, no such command is in the ${PATH}. Raise an exception.
    raise BetseMatplotlibException(
        'Matplotlib animation video writers {} '
        'not found in current ${{PATH}}.'.format(
            strs.join_as_conjunction_double_quoted(*writer_names)))


@type_check
def get_first_codec_name(
    writer_name: str, container_filetype: str, codec_names: SequenceTypes) -> str:
    '''
    Get the name of the first video codec (e.g., `libx264`) in the passed list
    supported by both the encoder with the passed matplotlib-specific name
    (e.g., `ffmpeg`) and the video container with the passed filetype (e.g.,
    `mkv`, `mp4`) if any _or_ raise an exception otherwise (i.e., if no such
    codecs are supported by both this encoder and container).

    This function iteratively searches for video codecs in the same order as
    listed in the passed list as follows:

    * If there are no remaining video codecs in this list to be examined, an
      exception is raised.
    * If the current video codec has the BETSE-specific name `auto`, the name of
      an intelligently selected codec supported by both this encoder and
      container if any is returned _or_ an exception is raised otherwise (i.e.,
      if no codecs are supported by both this encoder and container). Note that
      this codec's name rather than the BETSE-specific name `auto` is returned.
      See this function's body for further commentary.
    * Else if the current video codec is supported by both this encoder and
      container, this codec's name is returned.
    * Else the next video codec in this list is examined.

    Parameters
    ----------
    writer_name : str
        Matplotlib-specific alphanumeric lowercase name of the video encoder to
        search for the passed codecs.
    container_filetype: str
        Filetype of the video container format to constrain this search to.
    codec_names: SequenceTypes
        List of the encoder-specific names of all codecs to search for.

    Returns
    ----------
    str
        Name of the first codec in the passed list supported by both this
        encoder and container.

    Raises
    ----------
    BetseMatplotlibException
        If any of the following errors arise:
        * This writer is either:
          * Unrecognized by matplotlib or BETSE itself.
          * Not found as an external command in the current `${PATH}`.
        * This container format is unsupported by this writer.
        * No codec whose name is in the passed list is supported by both this
          writer and this container format.

    See Also
    ----------
    is_writer
        Tester validating this writer.
    '''

    # If this writer is unrecognized or not in the ${PATH}, raise an exception.
    die_unless_writer_pathable(writer_name)

    # Basename of this writer's command.
    writer_basename = WRITER_NAME_TO_COMMAND_BASENAME[writer_name]

    # Dictionary mapping from the filetype of each video container format to a
    # list of the names of all video codecs supported by this writer.
    container_filetype_to_codec_names = (
        WRITER_BASENAME_TO_CONTAINER_FILETYPE_TO_CODEC_NAMES[writer_basename])

    # If the passed container is unsupported by this writer, raise an exception.
    if container_filetype not in container_filetype_to_codec_names:
        raise BetseMatplotlibException(
            'Video container format "{}" unsupported by '
            'matplotlib animation video writer "{}".'.format(
                container_filetype, writer_name))

    # List of the names of all video codecs supported by this writer, used to
    # resolve passed codecs with the BETSE-specific name "auto".
    auto_codec_names = container_filetype_to_codec_names[container_filetype]

    # For the name of each passed codec...
    for codec_name in codec_names:
        # If this is the BETSE-specific name "auto"...
        if codec_name == 'auto':
            # For the name of each codec supported by this writer...
            for auto_codec_name in auto_codec_names:
                # If this writer supports this codec, return this name.
                if is_writer_command_codec(writer_basename, auto_codec_name):
                    return auto_codec_name
        # Else if this writer supports this codec, return this name.
        elif is_writer_command_codec(writer_basename, codec_name):
            return codec_name

    # Else, no passed codecs are supported by this combination of writer and
    # container format. Raise an exception.
    raise BetseMatplotlibException(
        'Video codec(s) {} unsupported by '
        'video container format "{}" and '
        'matplotlib animation video writer "{}".'.format(
            strs.join_as_conjunction_double_quoted(*codec_names),
            container_filetype,
            writer_name,
        ))

# ....................{ MAIN                               }....................
# Initialize all global variables declared by this submodule.
init()
