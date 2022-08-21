class LinkError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class BrokenEnvironment(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class TextLoader:

    @staticmethod
    def load(file_name: str) -> str:
        with open(file_name, 'r') as the_file:
            return the_file.read()
