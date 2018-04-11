"""
Module defining class-representation of module actions.

Each action class type encapsulates the user specified options available for
that specific action type. The action itself can be performed by invoking the
object method `execute()`.
"""

import abc
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Union

from jinja2.exceptions import TemplateNotFound
from mypy_extensions import TypedDict

from . import compiler
from .config import expand_path, insert_into

Replacer = Callable[[str], str]


class Action(abc.ABC):
    """
    Superclass for module action types.

    :param options: A dictionary containing the user options for a given module
        action type.
    :param directory: The directory used as anchor for relative paths. This
        must be an absolute path.
    :param replacer: Placeholder substitutor of string user options.
    """

    directory: Path
    priority: int

    def __init__(
        self,
        options: Union['ImportContextDict', 'CompileDict', 'RunDict'],
        directory: Path,
        replacer: Replacer,
        **kwargs,
    ) -> None:
        """Contstruct action object."""
        assert directory.is_absolute()
        self.directory = directory
        self._options = options
        self._replace = replacer

    def replace(self, string: str) -> str:
        """
        Return converted string, substitution defined by `replacer`.

        This is used to replace placeholders such as {event}.
        This redirection is necessary due to python/mypy/issues/2427

        :param string: String configuration option.
        :return: String with placeholders substituted.
        """
        return self._replace(string)

    def option(self, key: str, path: bool = False) -> Any:
        """
        Return user specified action option.

        All option value access should go through this helper function, as
        it replaces relevant placeholders users might have specified.

        :param key: The key of the user option that should be retrieved.
        :param path: If True, convert string path to Path.is_absolute().
        :return: Processed action configuration value.
        """
        option_value = self._options.get(key)

        if option_value is None:
            return None
        elif path:
            # The option value represents a path, that should be converted
            # to an absolute pathlib.Path object
            assert isinstance(option_value, str)
            substituted_string_path = self.replace(option_value)
            return self._absolute_path(of=substituted_string_path)
        elif isinstance(option_value, str):
            # The option is a string, and any placeholders should be
            # substituted before it is returned.
            return self.replace(option_value)
        else:
            return option_value

    def _absolute_path(self, of: str) -> Path:
        """
        Return absolute path from relative string path.

        :param of: Relative path.
        :return: Absolute path anchored to `self.directory`.
        """
        return expand_path(
            path=Path(of),
            config_directory=self.directory,
        )

    @abc.abstractmethod
    def execute(self) -> Any:
        """Execute defined action."""

    def __repr__(self) -> str:
        """Return string representation of Action object."""
        return self.__class__.__name__ + f'({self._options})'


class RequiredImportContextDict(TypedDict):
    """Required fields of a import_context action."""

    from_path: str


class ImportContextDict(RequiredImportContextDict, total=False):
    """Allowable fields of an import_context action."""

    from_section: str
    to_section: str


class ImportContextAction(Action):
    """
    Import context into global context store.

    :param context_store: A mutable reference to the global context store.

    See :class:`Action` for documentation for the other parameters.
    """

    priority = 100
    context_store: compiler.Context

    def __init__(
        self,
        options: ImportContextDict,
        directory: Path,
        replacer: Replacer,
        context_store: compiler.Context,
    ) -> None:
        """
        Contstruct import_context action object.

        Expands any relative paths relative to `self.directory`.
        """
        super().__init__(options, directory, replacer)
        self.context_store = context_store

    def execute(self) -> None:
        """Import context section(s) according to user configuration block."""
        insert_into(  # type: ignore
            context=self.context_store,
            from_config_file=self.option(key='from_path', path=True),
            section=self.option(key='to_section'),
            from_section=self.option(key='from_section'),
        )


class RequiredCompileDict(TypedDict):
    """Required fields of compile action."""

    template: str


class CompileDict(RequiredCompileDict, total=False):
    """Allowable fields of compile action."""

    target: str
    permissions: str


class CompileAction(Action):
    """Compile template action."""

    priority = 200

    def __init__(
        self,
        options: CompileDict,
        directory: Path,
        replacer: Callable[[str], str],
        context_store: compiler.Context,
    ) -> None:
        """
        Initialize compile action.

        :param context_store: A reference to a (not necessarily mutable)
            context store used as context for template compilation.
        """
        super().__init__(options, directory, replacer)
        self.context_store = context_store

    def execute(self) -> Path:
        """
        Compile template to target destination.

        :return: Path to compiled target.
        """
        template = self.option(key='template', path=True)
        target = self.option(key='target', path=True)
        if target is None:
            # A compilation target has not been specified, so we will compile
            # to a temporary file instead.
            target = self._create_temp_file(template.name)

        try:
            compiler.compile_template(
                template=template,
                target=target,
                context=self.context_store,
                shell_command_working_directory=self.directory,
                permissions=self.option(key='permissions'),
            )
        except TemplateNotFound:
            logger = logging.getLogger(__name__)
            logger.error(
                'Could not compile template '
                f'"{template}" to target "{target}". '
                'Template does not exist.',
            )
        return target

    def _create_temp_file(self, name) -> Path:
        """
        Create persisted tempory file.

        :return: Path object pointing to the created temporary file.
        """
        temp_file = NamedTemporaryFile(  # type: ignore
            prefix=name + '-',
            # dir=Path(self.temp_directory),
        )

        # NB: These temporary files need to be persisted during the entirity of
        # the scripts runtime, since the files are deleted when they go out of
        # scope.
        if not hasattr(self, 'temp_files'):
            self.temp_files = [temp_file]
        else:
            self.temp_files.append(temp_file)

        return Path(temp_file.name)


class RunDict(TypedDict):
    """Required fields of run action user config."""

    command: str


class RunAction(Action):
    """Run shell command action."""

    priority = 300

    def __init__(
        self,
        options: RunDict,
        directory: Path,
        replacer: Callable[[str], str],
    ) -> None:
        """Initialize shell command action."""
