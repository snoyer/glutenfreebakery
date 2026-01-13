import sys
from itertools import chain, islice
from typing import Callable, Generic, Iterable, Iterator, Sequence, TypeVar, overload

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
        self.explicit: list[T] = list(items) if items else []

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
        return iter(unique_by_id(chain(self.explicit, self.implicit)))

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

    def __iadd__(self, other: Iterable[T]):
        self.explicit += other
        return self

    def __eq__(self, value: object, /) -> bool:
        try:
            return type(value) is type(self) and all(
                a == b for a, b in zip(self, value, strict=True)
            )
        except (ValueError, TypeError):
            return False

    def __repr__(self) -> str:
        def f(xs: Iterable[T]):
            return ", ".join(f"<{type(x).__name__} object at 0x{id(x):0x}>" for x in xs)

        return f"<{type(self).__name__}([{f(self.explicit)}]+[{f(self.implicit)}])>"

    def replace(self, f: Callable[[T], T | None]):
        self._replace_implicits(f)
        self._replace_explicits(f)

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
