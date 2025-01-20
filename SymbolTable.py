class SymbolTable:
    def __init__(self):
        # For class-scope identifiers (static, field)
        self.class_scope = {}
        # For subroutine-scope identifiers (arg, var)
        self.subroutine_scope = {}
        # Keep counters for each kind
        self.indexes = {"static": 0, "field": 0, "arg": 0, "var": 0}

    def startSubroutine(self):
        """
        Reset subroutine scope and the 'arg'/'var' indices.
        Call this at the start of compiling each subroutine.
        """
        self.subroutine_scope.clear()
        self.indexes["arg"] = 0
        self.indexes["var"] = 0

    def define(self, name: str, type_: str, kind: str):
        """
        Define a new identifier of a given name, type, and kind.
        'kind' is one of ['static', 'field', 'arg', 'var'].
        """
        idx = self.indexes[kind]
        entry = {"type": type_, "kind": kind, "index": idx}

        if kind in ("static", "field"):
            self.class_scope[name] = entry
        else:
            self.subroutine_scope[name] = entry

        self.indexes[kind] += 1

    def varCount(self, kind: str):
        """Return # of variables of given kind."""
        return self.indexes[kind]

    def kindOf(self, name: str):
        """
        Return the kind of the named identifier: 'static', 'field', 'arg', 'var', or None.
        """
        if name in self.subroutine_scope:
            return self.subroutine_scope[name]["kind"]
        elif name in self.class_scope:
            return self.class_scope[name]["kind"]
        return None

    def typeOf(self, name: str):
        """Return the type of the named identifier."""
        if name in self.subroutine_scope:
            return self.subroutine_scope[name]["type"]
        elif name in self.class_scope:
            return self.class_scope[name]["type"]
        return None

    def indexOf(self, name: str):
        """Return the index of the named identifier."""
        if name in self.subroutine_scope:
            return self.subroutine_scope[name]["index"]
        elif name in self.class_scope:
            return self.class_scope[name]["index"]
        return None
