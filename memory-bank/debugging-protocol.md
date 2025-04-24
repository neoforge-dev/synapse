# Debugging Protocol

## Analysis Phase
When a test fails:
1. **Observe without judgment** - Note the exact error message and context
2. **Analyze the test case** - What is it verifying? What should the expected behavior be?
3. **Question assumptions** - Is the test correct? Is the implementation incomplete or incorrect?

## Systematic Investigation
- Run all tests in the same file to identify related failures
- Verify all required implementations exist for test dependencies
- Trace execution path from test to implementation, identifying gaps

## Implementation Phase
1. Implement the most minimal fix that addresses the root cause
2. Re-run tests to verify fix
3. Refactor if needed while maintaining passing tests

## Persistent Error Protocol
If the same error occurs twice:
- Step back and write 3 distinct reasoning paragraphs exploring different possible causes
- Review the entire component architecture, not just the specific function
- Consider edge cases, state management issues, and dependency problems

## Workflow
1. Make it work → Make it right → Make it fast
2. After tests pass, update memory bank and commit with descriptive message
3. Automatically continue to next priority task
4. Use Docker environments when appropriate

## Project-Specific Considerations

### Memgraph Integration
- When debugging Memgraph-related issues:
  - Verify connection state
  - Check query syntax
  - Validate data mapping between Pydantic models and Memgraph nodes
  - Use `GraphDebugger` for query inspection

### Vector Store Operations
- For vector store issues:
  - Verify embedding model initialization
  - Check vector dimensions match
  - Validate locking mechanism
  - Monitor memory usage

### API/CLI Integration
- When debugging API/CLI issues:
  - Check dependency injection
  - Verify request/response models
  - Validate error handling
  - Test both API and CLI paths

### Test Environment
- Use `conftest.py` fixtures consistently
- Mock external dependencies appropriately
- Maintain test isolation
- Use appropriate test markers

## Documentation Requirements
1. Document all fixes in `progress.md`
2. Update `active-context.md` with current focus
3. Add new patterns to `system-patterns.md`
4. Update `.neorules` with learned insights

Remember: Quiet the ego. TDD is about discovery, not being right the first time. 