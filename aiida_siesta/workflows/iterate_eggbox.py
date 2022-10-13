from .iterate import SiestaIterator
from .eggbox import SiestaEggboxWorkChain


class SiestaEggboxIterator(SiestaIterator):
    _process_class = SiestaEggboxWorkChain
