from .iterate import SiestaIterator
from .bdg_simple import SiestaBdGSimpleWorkChain


class SiestaBdGSimpleIterator(SiestaIterator):
    _process_class = SiestaBdGSimpleWorkChain
