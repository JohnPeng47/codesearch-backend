import functools
import random
import string
import uuid
import time
import functools
import os
from contextlib import contextmanager

from logging import getLogger

import os
import time
import shutil
import platform

if platform.system() == "Windows":
    import win32file
    import win32con
    import pywintypes
    import errno

logger = getLogger(__name__)


def delete_windows(path, max_attempts=5, delay=1):
    """
    Attempt to delete a file or directory on Windows, handling various edge cases.

    Args:
    path (str): Path to the file or directory to be deleted
    max_attempts (int): Maximum number of deletion attempts
    delay (float): Delay in seconds between attempts

    Returns:
    bool: True if deletion was successful, False otherwise
    """
    for attempt in range(max_attempts):
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
            print(f"Successfully deleted: {path}")
            return True
        except OSError as e:
            if e.errno == errno.EACCES:  # Permission error
                try:
                    # Change file/directory attributes to normal
                    win32file.SetFileAttributes(path, win32con.FILE_ATTRIBUTE_NORMAL)
                except pywintypes.error:
                    pass
            elif e.errno == errno.EBUSY:  # File/directory is in use
                print(f"Path is in use. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"Error deleting path: {e}")
                return False

        logger.error(
            f"Attempt delete {path}, attempt {attempt + 1} failed. Retrying..."
        )
        time.sleep(delay)

    print(f"Failed to delete {path} after {max_attempts} attempts.")
    return False


def rm_tree(path, max_attempts=5, delay=1):
    """
    Delete a file or directory on both Windows and other platforms.

    Args:
    path (str): Path to the file or directory to be deleted
    max_attempts (int): Maximum number of deletion attempts (for Windows only)
    delay (float): Delay in seconds between attempts (for Windows only)

    Returns:
    bool: True if deletion was successful, False otherwise
    """
    if platform.system() == "Windows":
        return delete_windows(path, max_attempts, delay)
    else:
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
            print(f"Successfully deleted: {path}")
            return True
        except Exception as e:
            print(f"Error deleting {path}: {e}")
            return False


@contextmanager
def set_temp_env_var(key, value):
    old_value = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if old_value is None:
            del os.environ[key]
        else:
            os.environ[key] = old_value


# nested level get() function
def resolve_attr(obj, attr, default=None):
    """Attempts to access attr via dotted notation, returns none if attr does not exist."""
    try:
        return functools.reduce(getattr, attr.split("."), obj)
    except AttributeError:
        return default


def gen_random_name():
    """
    Generates a random name using ASCII, 8 characters in length
    """

    return "".join(random.choices(string.ascii_lowercase, k=8))


def generate_id():
    """
    Generates a random UUID
    """
    return str(uuid.uuid4())


def async_timed(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        testgen_logger.info(
            f"[PARALLEL] Function {func.__name__} took {end_time - start_time:.4f} seconds"
        )
        return result

    return wrapper
