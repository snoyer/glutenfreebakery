import sys
from itertools import chain, islice
from typing import (
    Callable,
    Counter,
    Generic,
    Iterable,
    Iterator,
    Sequence,
    TypeVar,
    overload,
)

T = TypeVar("T")
P = TypeVar("P")


class PartiallyImplicitList(Generic[T, P], Sequence[T]):
    def __init__(
        self,
        items: Iterable[T] | None = None,
        *,
        parent: P | None = None,
    ) -> None:
        self.parent = parent
        self.explicit = list(items) if items else []
        self._preferred_order = {id(item): i for i, item in enumerate(self.explicit)}
        self.make_implicit()

    def make_implicit(self):
        """Remove implicit items from explicit list."""
        implicit_ids = {id(x) for x in self.implicit}
        self.explicit = list(
            unique_by_id(x for x in self.explicit if id(x) not in implicit_ids)
        )

    def __bool__(self):
        for _ in self:
            return True
        return False

    @property
    def implicit(self) -> Iterator[T]:
        if self.parent:
            yield from unique_by_id(filter(None, self._from_parent(self.parent)))

    def _from_parent(self, parent: P) -> Iterator[T | None]:
        return iter([])

    def __len__(self):
        n = 0
        for _ in self:
            n += 1
        return n

    def __iter__(self) -> Iterator[T]:
        def sort_key(item: T):
            return self._preferred_order.get(id(item), float("+inf"))

        unique = unique_by_id(chain(self.explicit, self.implicit))
        return iter(sorted(unique, key=sort_key))

    @overload
    def __getitem__(self, index: int) -> T: ...
    @overload
    def __getitem__(self, index: slice) -> Sequence[T]: ...
    def __getitem__(self, index: int | slice) -> Sequence[T] | T:
        if isinstance(index, slice):
            return list(islice(self, index.start, index.stop, index.step))
        else:
            i = index.__index__()
            try:
                return next(islice(self, i, i + 1))
            except StopIteration:
                raise IndexError(f"{index} not in {self}")

    def index(self, value: T, start: int = 0, stop: int = sys.maxsize):
        for i, x in enumerate(self):
            if start <= i < stop and id(x) == id(value):
                return i
        raise IndexError(value)

    def insert(self, index: int, item: T):
        self.explicit.insert(index, item)
        self._preferred_order[id(item)] = index
        self.make_implicit()

    def __iadd__(self, other: Iterable[T]):
        self.explicit += other
        self.make_implicit()
        return self

    def __eq__(self, value: object, /) -> bool:
        try:
            return type(value) is type(self) and all(
                a == b for a, b in zip(self, value, strict=True)
            )
        except (ValueError, TypeError):
            return False

    def __str__(self) -> str:
        def f(xs: Iterable[T], label: str):
            for t, n in Counter(map(type, xs)).items():
                yield f"{n} {label} {t.__name__}"

        items = chain(f(self.explicit, "explicit"), f(self.implicit, "implicit"))
        return f"<{type(self).__name__}({', '.join(items)})>"

    def replace(self, transform: Callable[[T], T | None]):
        """Replace each item with the result of the `transform` function applied to it."""
        self._replace_implicits(transform)
        self._replace_explicits(transform)

    def remove(self, predicate: Callable[[T], bool]):
        """Remove all items matching the `predicate` function."""
        return self.replace(lambda item: None if predicate(item) else item)

    def _replace_implicits(self, f: Callable[[T], T | None]) -> None:
        raise NotImplementedError()  # pragma: nocover

    def _replace_explicits(self, f: Callable[[T], T | None]):
        self.explicit = [new for old in self.explicit if (new := f(old)) is not None]


def unique_by_id(ts: Iterable[T]):
    seen_ids: set[int] = set()
    for t in ts:
        if id(t) not in seen_ids:
            yield t
            seen_ids.add(id(t))
