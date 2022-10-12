from collections import deque
from pathlib import Path
from typing import Iterable, Optional

import git
from loguru import logger
import tree_sitter


here = Path(__file__).resolve().parent
BUILD_DIR = here / "build"
VENDOR_DIR = here / "vendor"


def build_language(language: str) -> str:
    """
    Given a tree-sitter compatible language (i.e., included in https://github.com/tree-sitter), build a [shared library](https://en.wikipedia.org/wiki/Library_(computing)#Shared_libraries) for it via `tree_sitter.Language.build_library`. If necessary, the language library is cloned from its corresponding GitHub repository.

    Arguments:
        language (str): Name of the language.
    
    Returns:
        `str`: File path to the build shared library.
    """
    language_build_path = BUILD_DIR / f"{language}.so"
    BUILD_DIR.mkdir(exist_ok=True)
    language_repo = VENDOR_DIR / f"tree-sitter-{language}"
    if not language_repo.exists():
        language_repo_url = f"https://github.com/tree-sitter/tree-sitter-{language}"
        logger.info(f"Cloning {language_repo_url}")
        repo = git.Repo.clone_from(language_repo_url, language_repo)
    logger.info(f"Building language '{language}'")
    tree_sitter.Language.build_library(str(language_build_path), [str(language_repo)])
    return language_build_path


def get_parser(language: str) -> tree_sitter.Parser:
    """
    Given a language name, fetch the language shared library and retrieve its parser. If the shared object is not found in the predefined directory, it is built via `build_language`.

    Arguments:
        language (str): Name of the language.

    Returns:
        `tree_sitter.Parser`: The parser.
    """
    language_build_path = BUILD_DIR / f"{language}.so"
    if not language_build_path.exists():
        logger.info(f"No build for language '{language}'")
        language_build_path = build_language(language)
    parser = tree_sitter.Parser()
    parser.set_language(tree_sitter.Language(language_build_path, language))
    return parser


def traverse(ast: tree_sitter.Tree, method: Optional[str] = None) -> Iterable[tree_sitter.Node]:
    """
    Given an abstract syntax tree traverse it either breadth first or depth first.

    Arguments:
        ast (tree_sitter.Tree): abstract syntax tree to be traversed.
        method (str, optional): traversal method, one of 'breadth_first' or 'depth_first'.

    Returns:
        `Iterable[tree_sitter.Node]`: 
    """
    cursor = ast.walk()
    if method is None: method = "depth_first"
    if method == "breadth_first":
        yield from traverse_tree_breadth_first(cursor)
    elif method == "depth_first":
        yield from traverse_tree_depth_first(cursor)
    else:
        raise ValueError(f"Value for argument 'method' {method} not supported.")


def traverse_tree_depth_first(cursor: tree_sitter.TreeCursor) -> Iterable[tree_sitter.Node]:
    """
    Work horse function for `traverse`. Traverses a `tree_sitter.Tree` depth first.

    Arguments:
        cursor (tree_sitter.TreeCursor): a cursor to the tree.

    Returns:
        `Iterable[tree_sitter.Node]`
    """
    for child in cursor.node.children:
        yield child
        yield from traverse_tree_depth_first(child.walk())


def traverse_tree_breadth_first(cursor: tree_sitter.TreeCursor, q: Optional[deque] = None) -> Iterable[tree_sitter.Node]:
    """
    Work horse function for `traverse`. Traverses a `tree_sitter.Tree` breadth first.

    Arguments:
        cursor (tree_sitter.TreeCursor): a cursor to the tree.
        q (deque, optional): a queue of nodes to iterate over.

    Returns:
        `Iterable[tree_sitter.Node]`
    """
    if q is None:
        q = deque(cursor.node.children)
    for _ in range(len(q)):
        node = q.popleft()
        q.extend(node.walk().node.children)
        yield node
    if len(q) == 0:
        return
    yield from traverse_tree_breadth_first(cursor, q)
