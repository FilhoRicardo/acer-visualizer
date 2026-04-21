"""Tests for the upload-page transition guard in app.py.

The guard prevents the upload form from re-rendering after the user has
navigated away to the Graph View. It lives at the top of render_upload_pdf():

    if st.session_state.get('nav_selection') != "📤 Upload PDF":
        return

We test this structurally to avoid needing a live Streamlit server.
"""
import ast
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestNavTransitionGuard:
    """Verify the nav guard is correctly placed in render_upload_pdf()."""

    def _get_render_upload_pdf_source(self) -> str:
        """Read the render_upload_pdf function body from app.py as a string."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "src", "app.py")
        with open(app_path) as f:
            source = f.read()
        return source

    def test_render_upload_pdf_function_exists(self):
        """app.py must define render_upload_pdf."""
        source = self._get_render_upload_pdf_source()
        assert "def render_upload_pdf" in source

    def test_nav_guard_is_present(self):
        """render_upload_pdf() must have the nav_selection guard at its top."""
        source = self._get_render_upload_pdf_source()

        # Parse the AST
        tree = ast.parse(source)

        # Find the render_upload_pdf function
        render_fn = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "render_upload_pdf":
                render_fn = node
                break

        assert render_fn is not None, "render_upload_pdf() not found in app.py"

        # The very first statement in the function body must be the guard.
        # It will be an If node: if st.session_state.get('nav_selection') != "📤 Upload PDF":
        # The first statement might be a docstring (ast.Expr containing a Constant str).
        # Find the first real statement (non-docstring) as the guard.
        first_real_stmt = None
        for stmt in render_fn.body:
            if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)):
                first_real_stmt = stmt
                break

        assert first_real_stmt is not None, "render_upload_pdf() has no real statements (only docstring?)"
        assert isinstance(first_real_stmt, ast.If), (
            f"First real statement of render_upload_pdf() must be an if-guard, "
            f"found: {ast.dump(first_real_stmt)}"
        )

        # Verify it's checking nav_selection != "📤 Upload PDF"
        guard_source = ast.unparse(first_real_stmt.test)
        assert "nav_selection" in guard_source, (
            f"Guard condition must check 'nav_selection', got: {guard_source}"
        )
        assert "Upload PDF" in guard_source or "📤" in guard_source, (
            f"Guard must check against '📤 Upload PDF', got: {guard_source}"
        )

    def test_nav_guard_returns_early(self):
        """The guard must return (not continue) when nav_selection != Upload PDF."""
        source = self._get_render_upload_pdf_source()
        tree = ast.parse(source)

        render_fn = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "render_upload_pdf"
        )

        # Skip docstrings (ast.Expr with Constant str) to find the real first statement
        first_real_stmt = next((
            s for s in render_fn.body
            if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
        ), None)
        assert first_real_stmt is not None
        assert isinstance(first_real_stmt, ast.If)

        # Guard body must contain a Return
        guard_body = first_real_stmt.body
        assert any(isinstance(stmt, ast.Return) for stmt in guard_body), (
            "Guard if-block must contain a 'return' statement"
        )

        # The else clause of the guard should NOT exist (we want unconditional return)
        assert first_real_stmt.orelse == [], (
            "Guard if-statement should not have an else clause — "
            "it should unconditionally return"
        )

    def test_nav_guard_uses_get_not_direct_access(self):
        """Guard must use st.session_state.get() to avoid KeyError on missing key."""
        source = self._get_render_upload_pdf_source()
        assert "st.session_state.get('nav_selection')" in source, (
            "Guard should use st.session_state.get('nav_selection') "
            "to safely handle the case where the key hasn't been set yet"
        )

    def test_no_placeholder_comment_in_guard(self):
        """Guard must not be commented out or be a TODO/FIXME placeholder."""
        source = self._get_render_upload_pdf_source()

        # Check that the guard is real (uncommented) code
        # by verifying the ast If node exists and has a Return in its body
        tree = ast.parse(source)
        render_fn = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "render_upload_pdf"
        )

        # If it's a comment disguised as a string expr, ast won't catch it
        # but it also won't pass the "is If" check above. So this is already safe.
        first_real_stmt = next((
            s for s in render_fn.body
            if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
        ), None)
        assert first_real_stmt is not None
        assert isinstance(first_real_stmt, ast.If)

        # Additionally verify the guard body is not just 'pass'
        guard_body = first_real_stmt.body
        assert not (
            len(guard_body) == 1 and isinstance(guard_body[0], ast.Pass)
        ), "Guard body cannot be just 'pass' — it must return"

    def test_graph_build_sets_nav_to_graph_view(self):
        """After building the graph, nav_selection is set to '🕸️ Graph View'."""
        source = self._get_render_upload_pdf_source()
        # After extraction + build_graph_from_extraction, st.session_state['nav_selection'] is set
        assert "st.session_state['nav_selection']" in source
        assert "Graph View" in source
