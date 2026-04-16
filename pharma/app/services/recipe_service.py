"""
Recipe Service
Loads and retrieves master recipes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from ..domain.models import Recipe
from ..utils.persistence import get_by_id, load_all, save_all, upsert

ENTITY = "recipes"
_SEED_PATH = Path(__file__).parent.parent / "data" / "seed_recipes.json"


def load_seed_recipes() -> None:
    """Load seed recipes from JSON file if no recipes exist yet."""
    existing = load_all(ENTITY, Recipe)
    if existing:
        return
    if not _SEED_PATH.exists():
        return
    with open(_SEED_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    recipes = [Recipe.model_validate(r) for r in raw]
    save_all(ENTITY, recipes)


def get_all_recipes() -> List[Recipe]:
    load_seed_recipes()
    return load_all(ENTITY, Recipe)


def get_recipe(recipe_id: str) -> Optional[Recipe]:
    load_seed_recipes()
    return get_by_id(ENTITY, Recipe, "recipe_id", recipe_id)


def get_recipe_for_product(product_code: str) -> Optional[Recipe]:
    for r in get_all_recipes():
        if r.product_code == product_code:
            return r
    return None
