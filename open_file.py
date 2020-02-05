import os
from subprocess import run, CalledProcessError

import sublime
import sublime_plugin

try:
    from nt import _getfinalpathname
    from sys import getwindowsversion
    assert getwindowsversion().major >= 6

    def realpath(path):
        """Resolve symlinks and return real path to file.

        Note:
            This is a fix for the issue of `os.path.realpath()` not to resolve
            symlinks on Windows as it is an alias to `os.path.abspath()` only.
            see: http://bugs.python.org/issue9949

            This fix applies to local paths only as symlinks are not resolved
            by _getfinalpathname on network drives anyway.

            Also note that _getfinalpathname in Python 3.3 throws
            `NotImplementedError` on Windows versions prior to Windows Vista,
            hence we fallback to `os.path.abspath()` on these platforms.

        Arguments:
            path (string): The path to resolve.

        Returns:
            string: The resolved absolute path if exists or path as provided
                otherwise.
        """
        try:
            if path:
                real_path = _getfinalpathname(path)
                if real_path[5] == ':':
                    # Remove \\?\ from beginning of resolved path
                    return real_path[4:]
                return os.path.abspath(path)
        except FileNotFoundError:
            pass
        return path

except (AttributeError, ImportError, AssertionError):
    def realpath(path):
        """Resolve symlinks and return real path to file.

        Arguments:
            path (string): The path to resolve.

        Returns:
            string: The resolved absolute path.
        """
        return os.path.realpath(path) if path else None


def git_rev_parse(file_path, arg='--show-toplevel'):
    """Get Git repo path info from a file path.

    The file_path is converted to a absolute real path `git rev-parse`
    is run with that working directory.

    Note:
        This directly calls `git rev-parse` with your option.

    Arguments:
        file_path (string): Absolute path to a file.

    Returns:
        the git-related path.
    """
    rev_parse_path_args = {
        '--git-dir',
        '--absolute-git-dir',
        '--git-common-dir',
        '--show-toplevel',
        '--show-superproject-working-tree',
        '--shared-index-path',
    }
    if arg not in rev_parse_path_args:
        raise Exception('"arg" should be a `git rev-parse` '
                        'option with a single path output.')
    if file_path:
        path, name = os.path.split(realpath(file_path))
        try:
            completed_proc = run(['git', 'rev-parse', arg], cwd=path,
                                 capture_output=True)
            # print(completed_proc)
            if completed_proc.returncode:
                return None
            git_path = completed_proc.stdout.decode().strip()
            return git_path
        except CalledProcessError as e:
            pass
    return None


class GitOpenFileCommand(sublime_plugin.TextCommand):

    def __init__(self, id):
        sublime_plugin.TextCommand.__init__(self, id)
        self.repo = None

    def is_enabled(self):
        self.repo = git_rev_parse(self.view.file_name())
        return self.repo is not None

    def run(self, edit, file, rev_parse_arg=False, syntax=None):
        root = self.repo
        if rev_parse_arg:
            root = git_rev_parse(self.view.file_name(), rev_parse_arg)

        # TODO: fix when file (like .gitignore) does not exist
        view = self.view.window().open_file(
            os.path.join(root, file),
            sublime.TRANSIENT
        )
        if syntax:
            view.assign_syntax(syntax)
