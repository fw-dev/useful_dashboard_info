import sys


def get_web_username():
    if sys.platform == "darwin":
        return "_www"
    return "apache"
