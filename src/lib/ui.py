# -*- coding: utf8 -*-

import re
from termcolor import colored

COLORTBL = {
    "heading": { # Heading
        "title":    lambda m: colored(m, "yellow", attrs=["bold"]),
        "msg":      lambda m: colored(m, "yellow"),
    },
    "input": { # input
        "title":    lambda m: colored(m, "cyan", attrs=["bold"]),
        "msg":      lambda m: m,
    },
    "output": { # output
        "title":    lambda m: colored(m, "magenta", attrs=["bold"]),
        "msg":      lambda m: m,
    },
    "uq": { # unless_quiet
        "title":    lambda m: colored(m, "cyan"),
        "msg":      lambda m: colored(m, "grey", attrs=["bold"]),
    },
    "verbose": { # verbose
        "title":    lambda m: colored(m, "cyan"),
        "msg":      lambda m: colored(m, "grey", attrs=["bold"])
    },
    "error": {
        "title":    lambda m: colored(m, "red", attrs=["bold"]),
        "msg":      lambda m: m
    }
}

class show (object):
    NORMAL = 1
    QUIET = 0
    VERBOSE = 2

    verbosity = NORMAL

    @staticmethod
    def __show(col, title = None, msg = None, prepend = "", append = "", **kwargs):
        if kwargs.get('no_color', False):
            col = {"title": lambda m:m, "msg": lambda m:m}

        if title:
            if msg:
                msg = "%s %s" % (col["title"](title), col["msg"](msg))
            else:
                msg = col["title"](title)
        else:
            msg = col["msg"](msg)

        print("%s%s%s" % (prepend, msg, append))
        return True

    @classmethod
    def set_verbosity(cls, level):
        cls.verbosity = level
        return level


    @classmethod
    def error(cls, title = None, msg = None, **kwargs):
        """Shows error message"""
        return cls.__show(COLORTBL["error"], title, msg, **kwargs)

    # Show functions
    @classmethod
    def heading(cls, title = None, msg = None, **kwargs):
        """Displays heading"""
        return cls.__show(COLORTBL["heading"], title, msg, '\n=== ', ' ===', **kwargs)

    @classmethod
    def output(cls, title=None, msg = None, **kwargs):
        """Shows regular message"""
        return cls.__show(COLORTBL["output"], title, msg, **kwargs)

    @classmethod
    def unless_quiet(cls, msg = None, title = None, **kwargs):
        """Shows information unless in Quiet mode"""
        if cls.verbosity > cls.QUIET:
            return cls.__show(COLORTBL["uq"], title, msg, **kwargs)
        return True

    @classmethod
    def verbose(cls, msg = None, title = None , **kwargs):
        """Shows information on verbose mode"""

        if cls.verbosity >= cls.VERBOSE:
            return cls.__show(COLORTBL["verbose"], title, msg, **kwargs)
        return True


class ask (object):
    _input_func = raw_input

    @classmethod
    def mock_input_func(cls, fp):
        if is_callable(fp):
            cls._input_func = fp
        elif fp is None:
            cls._input_func = raw_input
        else:
            cls__input_func = lambda x: fp

    @staticmethod
    def opt():
        return COLORTBL["verbose"]["msg"]("(Opt) ")

    @staticmethod
    def title(title):
        return COLORTBL["input"]["title"](title)

    @classmethod
    def until(cls, title, cond, default = None, optional=False, return_groups = False):
        """
        Note: `strip()` inputs
        * return_groups: return matched groups if checked, else raw input
        """
        m = cond if callable(cond) else re.compile("^\s*%s\s*$" % cond).match

        while True:
            ret = cls._input_func("%s%s" % (
                cls.opt() if optional else "",
                cls.title(title))).strip()

            if '' == ret:
                if default is not None: return default
                if optional: return None

            if m(ret):
                if return_groups:
                    return m(ret).groups()
                return ret
            else:
                show.unless_quiet("Input %s doesn't match with regex %s" % (ret, cond))

    @classmethod
    def yn(cls, title, default=None):
        if default:
            title += " [Y/n]" if 'y' == default.lower() else ' [y/N]'
            title += ": "

        return cls.until(title, '[yYnN]', default=default)

    @classmethod
    def choose(cls, title, options = None, default=None, more_options=None):
        """Asks user to pick one from the list, 1-based index or full text in opt_list

        """

        opt_list = options if isinstance(options, list) else options.keys()

        show.output(
            title = COLORTBL["output"]["title"]("Options:"),
            msg = ", ".join([
                "[%d]%s" % (idx, COLORTBL["verbose"]["msg"](val))
                for idx, val in enumerate(opt_list, 1)]),
            no_color=True
        )

        while True:
            ret = cls._input_func(
                "%s%s: " % (
                    cls.title(title),
                    " [%s]" % default if default else ""))

            if '' == ret and default is not None:
                if type(default) is int:
                    ret = str(default)
                else:
                    return default

            if ret in opt_list:
                return ret if isinstance(options, list) else options[ret]

            if ret in more_options:
                return ret if isinstance(more_options, list) else more_options[ret]

            if ret.isdigit():
                ret = int(ret)-1
                if ret >= 0 and ret < len(opt_list):
                    return opt_list[ret] if isinstance(options, list) else options[opt_list[ret]]
