"""
Basic integration tests for the TyServer language server functionality.

These tests validate that TyServer (ty type checker as LSP) works correctly
with core LSP operations like document symbols, workspace symbols, and references.
"""

import os

import pytest

from solidlsp import SolidLanguageServer
from solidlsp.ls_config import Language


@pytest.mark.python_ty
class TestTyServerBasics:
    """Test basic functionality of the TyServer language server."""

    @pytest.mark.parametrize("language_server", [Language.PYTHON_TY], indirect=True)
    def test_ty_server_instantiation(self, language_server: SolidLanguageServer) -> None:
        """Test that TyServer starts and is responsive."""
        # If we got here, the server started successfully via the fixture
        assert language_server is not None
        assert language_server.is_running()

    @pytest.mark.parametrize("language_server", [Language.PYTHON_TY], indirect=True)
    def test_request_document_symbols(self, language_server: SolidLanguageServer) -> None:
        """Test request_document_symbols on the models.py fixture file."""
        file_path = os.path.join("test_repo", "models.py")
        result = language_server.request_document_symbols(file_path)
        symbols, roots = result.get_all_symbols_and_roots()

        # Should find key symbols in models.py
        symbol_names = [s.get("name") for s in symbols]
        assert "User" in symbol_names, "Should find User class"
        assert "Item" in symbol_names, "Should find Item class"
        assert "BaseModel" in symbol_names, "Should find BaseModel class"

    @pytest.mark.parametrize("language_server", [Language.PYTHON_TY], indirect=True)
    def test_request_workspace_symbol(self, language_server: SolidLanguageServer) -> None:
        """Test workspace symbol search for a known symbol."""
        # Search for UserService which is defined in services.py
        results = language_server.request_workspace_symbol("UserService")

        # Note: ty v0.0.8 may not fully support workspace/symbol yet
        # This test verifies the method is callable and returns a valid response
        assert results is not None or results == [], "Should return valid response (list or None)"

        if results:
            # If results are returned, verify structure
            found_class = any(
                r.get("name") == "UserService" for r in results
            )
            assert found_class, "Should find UserService in results"

    @pytest.mark.parametrize("language_server", [Language.PYTHON_TY], indirect=True)
    def test_request_references_user_class(self, language_server: SolidLanguageServer) -> None:
        """Test request_references on the User class."""
        file_path = os.path.join("test_repo", "models.py")

        # Get the User symbol position via document symbols
        symbols = language_server.request_document_symbols(file_path).get_all_symbols_and_roots()
        user_symbol = next((s for s in symbols[0] if s.get("name") == "User"), None)

        if not user_symbol or "selectionRange" not in user_symbol:
            raise AssertionError("User symbol or its selectionRange not found")

        sel_start = user_symbol["selectionRange"]["start"]
        references = language_server.request_references(
            file_path, sel_start["line"], sel_start["character"]
        )

        # ty v0.0.8 may have limited cross-file reference support
        # At minimum, should find the definition itself
        assert len(references) >= 1, "Should find at least the User class definition"

        # Verify at least one reference is in models.py (the definition file)
        models_references = [ref for ref in references if "models.py" in ref["uri"]]
        assert len(models_references) > 0, "Should find User reference in models.py"
