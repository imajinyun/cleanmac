"""CLI parser and command router for CleanMac."""

from .core import add_category_flags, main, normalize_grouped_argv, parse_args, select_categories

__all__ = ["add_category_flags", "main", "normalize_grouped_argv", "parse_args", "select_categories"]
