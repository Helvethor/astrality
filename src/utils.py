"""General utility functions which are used across the application."""

import logging
from pathlib import Path
import subprocess


logger = logging.getLogger('astrality')


def run_shell(command: str, working_directory: Path = Path.home()) -> str:
    """Return the standard output of a shell command."""

    process = subprocess.Popen(
        command,
        cwd=working_directory,
        shell=True,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        process.wait(timeout=2)

        for error_line in process.stderr:
            logger.error(str(error_line))

        if process.returncode != 0:
            logger.error(
                f'Command "{command}" exited with non-zero return code: ' +
                str(process.returncode)
            )
            return ''
        else:
            stdout = process.communicate()[0]
            logger.info(stdout)
            return stdout.replace('\n', '')

    except subprocess.TimeoutExpired:
        logger.warning(
            f'The command "{command}" used more than 2 seconds in order to '
            'finish. The exit code can not be verified. This might be '
            'intentional for background processes and daemons.'
        )
        return ''
