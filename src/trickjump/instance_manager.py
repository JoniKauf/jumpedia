

from typing import Any, Callable, Hashable, Iterable, Optional as Opt
import threading

class InstanceManager[InstanceT, LookupT: Hashable]():
    def __init__(
        self, 
        get_lookups: Callable[[InstanceT], Iterable[LookupT]],
        on_add: Opt[Callable[[InstanceT], None]] = None,
        on_remove: Opt[Callable[[InstanceT], None]] = None
    ) -> None:
        self._on_add = on_add
        self._on_remove = on_remove
        self._get_lookups = get_lookups
        self._all: list[InstanceT] = []
        self._lookup: dict[LookupT, InstanceT] = {}
        self._LOCK = threading.RLock()
    
    def lookup(self, lookup: LookupT) -> InstanceT:
        return self._lookup[lookup]  # atomic operation
    
    def all_instances(self) -> list[InstanceT]:
        with self._LOCK:
            return list(self._all)
    
    def get_lookups(self, instance: InstanceT) -> tuple[LookupT, ...]:
        with self._LOCK:
            return tuple(k for k, v in self._lookup.items() if v == instance)
    
    def add(self, instance: InstanceT) -> None:
        with self._LOCK:
            lookup_values = self._get_lookups(instance)
            
            if instance in self._all:
                raise ValueError("Instance already in added")
            
            self._all.append(instance)

            for lv in lookup_values:
                if lv in self._lookup:
                    raise ValueError("lookup value already used for different instance")
                
                self._lookup[lv] = instance
        
        self._on_add
   
    def remove(self, instance: InstanceT):
        with self._LOCK:
            for k, v in self._lookup.items():
                if v == instance:
                    self._lookup.pop(k)
            
            self._all.remove(instance)

        self._on_remove