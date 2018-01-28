import logging
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile
from typing import Dict, IO
import os

from compiler import compile_template
from resolver import Resolver


logger = logging.getLogger('astrality')


def compile_conky_templates(
    config: Resolver,
    period: str,
) -> None:
    tempfiles = config['_runtime']['conky_temp_files']
    templates = config['_runtime']['conky_module_templates']

    for module, template_path in templates.items():
        compile_template(
            template=template_path,
            target=tempfiles[module].name,
            period=period,
            config=config,
        )

def create_conky_temp_files(
    temp_directory: Path,
    conky_module_templates: Dict[str, Path],
) -> Dict[str, IO]:
    # NB: These temporary files/directories need to be persisted during the
    # entirity of the scripts runtime, since the files are deleted when they
    # go out of scope

    conky_temp_files = {
        module: NamedTemporaryFile( # type: ignore
            prefix=module + '-',
            dir=temp_directory
        )
        for module, path
        in conky_module_templates.items()
    }

    for temp_file in conky_temp_files.values():
        # TODO: There are probably security implications here.
        # I am not sure how this should be done, as temporary files can be
        # used arbitrarily by the user, and we should support all use cases.
        os.chmod(temp_file.name, 0o777)

    return conky_temp_files

def start_conky_process(config: Resolver) -> None:
    conky_temp_files = config['_runtime']['conky_temp_files']
    for module_path, file in conky_temp_files.items():
        logger.info(f'Initializing conky module "{module_path}"')
        logger.info(f'    Tempory file placed at "{file.name}"')
        subprocess.Popen(['conky', '-c', file.name])
