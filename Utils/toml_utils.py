# pylint: disable=line-too-long,invalid-name,pointless-string-statement,too-many-arguments,too-many-locals
"""
Utils for TOML files.
"""
from typing import Any
import pathlib
import tomllib


def print_nested_dicts(data: Any, num_identation: int = 0, identation_type: str = '\t') -> None:
    """Prints nested dictionaries, each with an identation."""
    if isinstance(data, dict):
        if num_identation > 0:
            print()
        for k, v in data.items():
            print(f"{identation_type * num_identation}{k}", end='')
            print_nested_dicts(v, num_identation=num_identation+1, identation_type=identation_type)
    else:
        print(f" = {data}")

class myToml_read:
    """
    Reading and displaying TOML file, using the (built-in) python tomllib package.

    Use this if the package toml is not installed, otherwise, use the myToml class.
    """
    __data: dict = {}

    def load(self, filename: pathlib.Path) -> dict:
        """Reads TOML file."""
        try:
            with open(filename, 'rb') as fp:
                self.__data = tomllib.load(fp)
        except FileNotFoundError:
            print(f"Cannot find {filename} !!")
        return self.__data

    def show(self) -> None:
        """print the data"""
        print_nested_dicts(self.__data)

    def get_data(self) -> dict:
        return self.__data

    def __repr__(self):
        return "myToml())"

    def __str__(self):
        return "Reading and displaying TOML file.\n"

class myToml:
    """
    Reading, writing, and displaying TOML files.

    Requires the package toml (pip install toml)
    """
    import toml

    __data: dict = {}  # holds the recent TOML data

    def load(self, filename: pathlib.Path) -> dict:
        """Reads TOML file."""
        try:
            with open(filename, 'r') as fp:
                self.__data = self.toml.load(fp)
        except FileNotFoundError:
            print(f"Cannot find {filename} !!")
        return self.__data
        
    def dump(self, data: dict, filename: pathlib.Path) -> None:
        """Writes data to a TOML file"""
        with open(filename, 'w') as fp:
            self.toml.dump(data, fp)

    def get_data(self) -> dict:
        return self.__data

    def show(self):
        """prints the data with """
        print_nested_dicts(self.__data)

    def __repr__(self):
        return "myToml())"

    def __str__(self):
        return "Reading, writing, and displaying TOML file.\n"