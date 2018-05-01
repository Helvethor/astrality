import os
from pathlib import Path
from shutil import rmtree

import pytest

from astrality import compiler
from astrality.config import (
    create_config_directory,
    dict_from_config_file,
    user_configuration,
    resolve_config_directory,
)
from astrality.context import Context
from astrality.utils import generate_expanded_env_dict


@pytest.fixture
def dummy_config():
    test_conf = Path(__file__).parents[1] / 'test_config' / 'test.yml'
    return dict_from_config_file(
        config_file=test_conf,
        context=Context(),
    )


class TestAllConfigFeaturesFromDummyConfig:
    def test_normal_variable(self, dummy_config):
        assert dummy_config['section1']['var1'] == 'value1'

    def test_variable_interpolation(self, dummy_config):
        assert dummy_config['section1']['var2'] == 'value1/value2'
        assert dummy_config['section2']['var3'] == 'value1'

    def test_empty_string_variable(self, dummy_config):
        assert dummy_config['section2']['empty_string_var'] == ''

    def test_non_existing_variable(self, dummy_config):
        with pytest.raises(KeyError):
            assert dummy_config['section2']['not_existing_option'] \
                is None

    def test_environment_variable_interpolation(self, dummy_config):
        assert dummy_config['section3']['env_variable'] \
            == 'test_value, hello'


def test_config_directory_name(conf):
    assert str(conf['_runtime']['config_directory'])[-7:] == '/config'


def test_name_of_config_file(conf):
    assert '/astrality.yml' in str(conf['_runtime']['config_file'])


def test_generation_of_expanded_env_dict():
    env_dict = generate_expanded_env_dict()
    assert len(env_dict) == len(os.environ)

    for name, value in os.environ.items():
        if '$' not in value:
            assert env_dict[name] == value


class TestResolveConfigDirectory:
    def test_setting_directory_using_application_env_variable(
        self,
        monkeypatch,
    ):
        monkeypatch.setattr(
            os,
            'environ',
            {
                'ASTRALITY_CONFIG_HOME': '/test/dir',
                'XDG_CONFIG_HOME': '/xdg/dir',
            },
        )
        assert resolve_config_directory() == Path('/test/dir')

    def test_setting_directory_using_xdg_directory_standard(self, monkeypatch):
        monkeypatch.setattr(
            os,
            'environ',
            {
                'XDG_CONFIG_HOME': '/xdg/dir',
            },
        )
        assert resolve_config_directory() == Path('/xdg/dir/astrality')

    def test_using_standard_config_dir_when_nothing_else_is_specified(
        self,
        monkeypatch,
    ):
        monkeypatch.setattr(os, 'environ', {})
        assert resolve_config_directory() \
            == Path('~/.config/astrality').expanduser()


class TestCreateConfigDirectory:
    def test_creation_of_empty_config_directory(self):
        config_path = Path('/tmp/config_test')
        config_dir = create_config_directory(path=config_path, empty=True)
        assert config_path == config_dir
        assert config_dir.is_dir()
        assert len(list(config_dir.iterdir())) == 0
        config_dir.rmdir()

    def test_creation_of_infered_config_directory(self, monkeypatch):
        config_path = Path('/tmp/astrality_config')
        monkeypatch.setattr(
            os,
            'environ',
            {'ASTRALITY_CONFIG_HOME': str(config_path)},
        )
        created_config_dir = create_config_directory(empty=True)
        assert created_config_dir == config_path
        created_config_dir.rmdir()

    def test_creation_of_config_directory_with_example_content(self):
        """Test copying example configuration contents."""
        config_path = Path('/tmp/astrality_config_with_contents')
        created_config_dir = create_config_directory(config_path)
        assert created_config_dir == config_path

        # Test presence of content in created folder
        dir_contents = tuple(file.name for file in created_config_dir.iterdir())
        assert 'astrality.yml' in dir_contents
        assert 'modules' in dir_contents
        rmtree(created_config_dir)


@pytest.yield_fixture
def dir_with_compilable_files(tmpdir):
    config_dir = Path(tmpdir)
    config_file = config_dir / 'astrality.yml'
    config_file.write_text(
        'key1: {{ env.EXAMPLE_ENV_VARIABLE }}\n'
        'key2: {{ "echo test" | shell }}'
    )

    module_file = config_dir / 'modules.yml'
    module_file.write_text(
        'key1: {{ env.EXAMPLE_ENV_VARIABLE }}\n'
        'key2: {{ "echo test" | shell }}'
    )

    yield config_dir

    os.remove(config_file)
    os.remove(module_file)
    config_dir.rmdir()


class TestUsingConfigFilesWithPlaceholders:
    def test_dict_from_config_file(self, dir_with_compilable_files):
        config = dict_from_config_file(
            config_file=dir_with_compilable_files / 'astrality.yml',
            context={},
        )
        assert config == {
            'key1': 'test_value',
            'key2': 'test',
        }

    def test_get_user_configuration(self, dir_with_compilable_files):
        user_conf, _ = user_configuration(dir_with_compilable_files)
        assert user_conf['config/key1'] == 'test_value'
        assert user_conf['config/key2'] == 'test'
