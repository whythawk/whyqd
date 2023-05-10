from __future__ import annotations
from typing import Generic, TypeVar, Type
from pydantic import BaseModel
from uuid import UUID

ModelType = TypeVar("ModelType", bound=BaseModel)


class CRUDBase(Generic[ModelType]):
    """
    CRUD object with default methods to Create, Read, Update, Delete (CRUD).

    Parameters:
      model: A Pydantic model class
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model
        self.multi = []

    def get(self, *, name: str | UUID) -> ModelType | None:
        """Get a specific model from the list of models defining this schema, called by a unique `name`.

        Parameters:
          name: Specific name or reference UUID for a field already in the Schema.

        Returns:
          ModelType, or None if no such `name` or `UUID`.
        """
        name = self.get_hex(name=name)
        if self.multi:
            # https://stackoverflow.com/a/31988734/295606
            # It is statistically almost impossible to have a field name that matches a randomly-generated UUID
            # Can be used to recover fields from hex
            return next((m for m in self.multi if m.name == name or m.uuid.hex == name), None)
        return None

    def get_all(self) -> list[ModelType]:
        """Get all models from the current list of models."""
        return self.multi

    def add(self, *, term: ModelType | dict) -> None:
        """Add the parameters for a specific term, called by a unique `name`. If the `name` already exists, then this
        will raise a `ValueError`.

        Parameters:
          term: A dictionary conforming to the ModelType. Model names must be unique, so a valid `name` in the model list
                will have no collisions.

        Raises:
          ValueError: If the term already exists.
        """
        if isinstance(term, dict):
            term = self.model(**term)
        if self.get(name=term.name):
            raise ValueError(f"ModelType {term.name} already exists.")
        self.multi.append(term)

    def add_multi(self, *, terms: list[ModelType | dict]) -> None:
        """Add multiple parameters for a specific term, called by a unique `name`. If the `name` already exists, then
        this will raise a `ValueError`.

        Parameters:
          terms: A list of dictionaries conforming to the ModelType.

        Raises:
          ValueError: If the term already exists.
        """
        for term in terms:
            self.add(term=term)

    def update(self, *, term: ModelType | dict) -> None:
        """Update the parameters for a specific term, called by a unique `name`. If the `name` does not exist, then
        this will raise a `ValueError`.

        Parameters:
          term: A dictionary conforming to the ModelType.

        Raises:
          ValueError: If the term does not exist
        """
        if isinstance(term, dict):
            term = self.model(**term)
        # Create a temporary FieldModel
        old_term = self.get(name=term.name)
        if not old_term:
            raise ValueError(f"ModelType {term.name} does not exist.")
        # And update the original data
        old_name = old_term.name
        # https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
        old_term = old_term.copy(update=term.dict(exclude_unset=True))
        self.remove(name=old_name)
        self.add(term=old_term)

    def remove(self, *, name: str) -> None:
        """Remove a specific term, called by a unique `name`.

        Parameters:
          name: Specific name or reference UUID for a field already in the Schema.
        """
        # https://stackoverflow.com/a/1235631/295606
        name = self.get_hex(name=name)
        self.multi[:] = [m for m in self.multi if m.name != name and m.uuid.hex != name]

    def reset(self) -> None:
        """Reset a list of ModelType terms to an empty list."""
        self.multi = []

    def reorder(self, *, order: list[UUID]) -> None:
        """Reorder a list of terms.

        Parameters:
          order: list of UUID in the desired order. Use `.get_all()` to view the current list.

        Raises:
          ValueError: If the list of `UUIDs` doesn't conform to that in the list of terms.
        """
        order = [self.get_hex(name=o) for o in order]
        if {m.uuid.hex for m in self.multi}.difference(set(order)):
            raise ValueError("List of reordered term ids isn't the same as that in the provided list of Models.")
        if self.multi:
            self.multi = sorted(self.multi, key=lambda term: order.index(term.uuid.hex))

    def get_hex(self, *, name: str | UUID) -> str:
        if isinstance(name, UUID):
            return name.hex
        return name
