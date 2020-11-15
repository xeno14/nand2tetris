from constants import SymbolKind
from typing import *

import collections


class Symbol:

    def __init__(self, name: str, type: str, kind: SymbolKind, index: int=0):
        self.name = name
        self.type = type
        self.kind = kind
        self.index = index
    
    def __str__(self):
        return str((self.name, self.type, self.kind.name, self.index))
    
    def __repr__(self):
        return str(self)


class SymbolTable:

    def __init__(self):
        self.table: Dict[str, Symbol] = {}
        self.counter = {
            SymbolKind.STATIC: 0,
            SymbolKind.FIELD: 0,
            SymbolKind.ARG: 0,
            SymbolKind.VAR: 0
        }
    
    def define(self, name: str, type: str, kind: SymbolKind):
        """defines a new identifier
        """
        if name in self.table:
            raise RuntimeError("%s already defined in this scope" % name)
        index = self.counter[kind]
        self.counter[kind] += 1
        self.table[name] = Symbol(name, type, kind, index)

    def kind_of(self, name: str) -> SymbolKind:
        return self.table.get(name, SymbolKind.UNKNOWN)
    
    def type_of(self, name: str) -> str:
        return self.table.get(name, "")
    
    def index_of(self, name: str) -> int:
        return self.table.get(name, -1)
    

def _test():
    table = SymbolTable()
    table.define("x", "int", SymbolKind.FIELD)
    table.define("y", "int", SymbolKind.FIELD)
    table.define("this", "Point", SymbolKind.ARG)   
    table.define("other", "Point", SymbolKind.ARG)   
    table.define("dx", "int", SymbolKind.VAR)   
    table.define("dy", "int", SymbolKind.VAR)
    
    import pprint
    pprint.pprint(table.table)


if __name__ == "__main__":
    _test()
