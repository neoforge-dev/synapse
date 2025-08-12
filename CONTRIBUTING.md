# Contributing to Synapse MCP

Thank you for considering contributing to the Synapse MCP project!

## How to Contribute

1.  **Find an issue or propose an idea:** Check the issue tracker for existing tasks or bugs. If you have a new idea or feature request, please open an issue first to discuss it.
2.  **Fork the repository:** Create your own copy of the repository.
3.  **Create a branch:** Create a descriptive branch name for your feature or bug fix (e.g., `feat/add-cli-ingestion` or `fix/search-streaming-error`).
4.  **Make your changes:** Implement your feature or fix the bug.
5.  **Ensure code quality:**
    *   **Formatting:** Run `make format` (ruff format).
    *   **Linting/Types:** Run `make lint` (ruff check + mypy on core/services).
    *   *(Optionally configure pre-commit hooks if available)*
6.  **Write tests:** Add unit or integration tests for any new functionality.
7.  **Run tests:** Ensure all tests pass by running `make test` (see README for env setup). For hot-path coverage: `make coverage-hot`.
8.  **Commit your changes:** Write clear and concise commit messages.
9.  **Push to your fork:** Push your changes to your branch on your fork.
10. **Create a Pull Request:** Open a Pull Request (PR) from your branch to the main repository's `main` branch. Provide a clear description of your changes in the PR.

## Code Style

*   Follow PEP 8 guidelines.
*   Use Ruff and Black for formatting and linting.
*   Use MyPy for type checking.
*   Write clear and documented code.

## Questions?

Feel free to open an issue if you have questions about contributing. 