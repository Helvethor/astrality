import os
from pathlib import Path

from astrality.actions import CompileAction

def test_null_object_pattern():
    """Compilation action with no parameters should be a null object."""
    compile_action = CompileAction(
        options={},
        directory=Path('/'),
        replacer=lambda x: x,
        context_store={},
    )
    target = compile_action.execute()
    assert target is None


def test_compilation_of_template_to_temporary_file(template_directory):
    """Compile template to temporary file in absence of `target`."""
    compile_dict = {
        'template': 'no_context.template',
    }
    compile_action = CompileAction(
        options=compile_dict,
        directory=template_directory,
        replacer=lambda x: x,
        context_store={},
    )
    target = compile_action.execute()

    assert target.read_text() == 'one\ntwo\nthree'

def test_compilation_to_specific_absolute_file_path(template_directory, tmpdir):
    """
    Compile to specified absolute target path.

    The template is specified relatively.
    """
    target = Path(tmpdir) / 'target'
    compile_dict = {
        'template': 'no_context.template',
        'target': str(target),
    }
    compile_action = CompileAction(
        options=compile_dict,
        directory=template_directory,
        replacer=lambda x: x,
        context_store={},
    )
    return_target = compile_action.execute()

    assert return_target == target
    assert target.read_text() == 'one\ntwo\nthree'

def test_compilation_to_specific_relative_file_path(template_directory, tmpdir):
    """
    Compile to specified absolute target path.

    The template is specified absolutely.
    """
    target = Path(tmpdir) / 'target'
    compile_dict = {
        'template': str(template_directory / 'no_context.template'),
        'target': str(target.name),
    }
    compile_action = CompileAction(
        options=compile_dict,
        directory=Path(tmpdir),
        replacer=lambda x: x,
        context_store={},
    )
    return_target = compile_action.execute()

    assert return_target == target
    assert target.read_text() == 'one\ntwo\nthree'

def test_compilation_with_context(template_directory):
    """
    Templates should be compiled with the context store.

    It should compile differently after mutatinig the store.
    """
    compile_dict = {
        'template': 'test_template.conf',
    }
    context_store = {}

    compile_action = CompileAction(
        options=compile_dict,
        directory=template_directory,
        replacer=lambda x: x,
        context_store=context_store,
    )

    context_store['fonts'] = {2: 'ComicSans'}
    target = compile_action.execute()

    username = os.environ.get('USER')
    assert target.read_text() == f'some text\n{username}\nComicSans'

    context_store['fonts'] = {2: 'TimesNewRoman'}
    target = compile_action.execute()
    assert target.read_text() == f'some text\n{username}\nTimesNewRoman'

def test_setting_permissions_of_target_template(template_directory):
    """Template target permission bits should be settable."""
    compile_dict = {
        'template': 'empty.template',
        'permissions': '707',
    }
    compile_action = CompileAction(
        options=compile_dict,
        directory=template_directory,
        replacer=lambda x: x,
        context_store={},
    )

    target = compile_action.execute()
    assert (target.stat().st_mode & 0o777) == 0o707

def test_use_of_replacer(template_directory, tmpdir):
    """All options should be run through the replacer."""
    compile_dict = {
        'template': 'template',
        'target': 'target',
        'permissions': 'permissions',
    }

    template = template_directory / 'no_context.template'
    target = Path(tmpdir) / 'target'

    def replacer(string: str) -> str:
        """Trivial replacer."""
        if string == 'template':
            return template.name
        elif string == 'target':
            return str(target)
        else:
            return '777'

    compile_action = CompileAction(
        options=compile_dict,
        directory=template_directory,
        replacer=replacer,
        context_store={},
    )

    target = compile_action.execute()
    assert target.read_text() == 'one\ntwo\nthree'
    assert (target.stat().st_mode & 0o777) == 0o777

def test_that_current_directory_is_set_correctly(template_directory):
    """Shell commmand filters should be run from `directory`."""
    compile_dict = {
        'template': str(
            template_directory / 'shell_filter_working_directory.template',
        ),
    }

    directory=Path('/tmp')
    compile_action = CompileAction(
        options=compile_dict,
        directory=directory,
        replacer=lambda x: x,
        context_store={},
    )
    target = compile_action.execute()
    assert target.read_text() == '/tmp'