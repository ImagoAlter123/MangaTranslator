"""Normalize model-generated line breaks without decoding other escapes."""
import re


def normalize_translation(text):
    # Some models emit literal backslash+n (sometimes double-escaped) instead
    # of a real newline. Do not use unicode_escape: it damages CJK and symbols.
    text = re.sub(r'\\+r\\+n|\\+n|\\+r', '\n', text)
    return text.replace('\r\n', '\n').replace('\r', '\n')
