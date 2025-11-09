# Documentation Link Validation

This document describes the automated link validation system for the Synapse Graph-RAG project.

## Overview

The project uses automated link checking in CI/CD to ensure all documentation links remain valid and prevent broken references. This is implemented using [lychee](https://github.com/lycheeverse/lychee), a fast and reliable link checker.

## Workflow Details

### When It Runs

The link validation workflow (`docs-validation.yml`) runs automatically on:

1. **Push to main/develop branches** - When markdown files are modified
2. **Pull requests** - Validates links in PR changes
3. **Weekly schedule** - Every Monday at 8am UTC to catch external link rot
4. **Manual dispatch** - Can be triggered manually from the Actions tab

### What It Checks

The workflow validates:

- All internal links (references to files within the repository)
- All external links (HTTP/HTTPS URLs to external resources)
- Markdown files with `.md` or `.markdown` extensions
- Links in all directories (excluding common build/cache directories)

### What It Ignores

The following patterns are excluded from validation (see `.lycheeignore`):

- Local development URLs (`localhost`, `127.0.0.1`, `0.0.0.0`)
- Placeholder URLs (`example.com`, template GitHub URLs)
- Authentication-required APIs (LinkedIn, OpenAI, Anthropic)
- Mailto links (not checkable via HTTP)
- File protocol URLs
- GitHub Actions run URLs (may not be publicly accessible)

## Configuration

### Link Checker Settings

The workflow is configured with sensible defaults:

```yaml
--timeout 30           # 30 second timeout for external links
--max-redirects 10     # Follow up to 10 redirects
--max-retries 3        # Retry failed links 3 times
--retry-wait-time 2    # Wait 2 seconds between retries
--accept 200,204,301,429  # Accept these HTTP status codes
```

### Caching

Link check results are cached to improve performance:

- Cache is stored in `.lycheecache`
- Cache expires after 1 day
- Reduces redundant checks for unchanged links
- Significantly speeds up subsequent runs

## Viewing Results

### In GitHub Actions

1. Go to the **Actions** tab in the GitHub repository
2. Click on **Documentation Validation** workflow
3. Select the specific run you want to review
4. Click on the **Check Markdown Links** job
5. Expand the **Check all markdown links** step to see detailed results

### In Pull Requests

If link validation fails on a PR:

1. A comment will be automatically added to the PR
2. The comment includes:
   - Summary of the failure
   - Next steps to fix the issue
   - Common causes of broken links
   - Link to the full workflow run

### Artifacts

Each run generates a link check report artifact:

1. Click on the workflow run
2. Scroll to **Artifacts** section at the bottom
3. Download **link-check-report** for detailed statistics

## Fixing Broken Links

### Common Issues and Solutions

#### 1. Internal Link Broken

**Problem**: `docs/guide/setup.md` → `docs/setup.md` doesn't exist

**Solution**:
- Verify the file exists at the referenced path
- Check for typos in the filename or path
- Update the link if the file was moved
- Use relative paths from the current file location

#### 2. External Link Unavailable

**Problem**: External website returns 404 or is unreachable

**Solution**:
- Verify the URL is correct
- Check if the page was moved (use web search to find new URL)
- Replace with an alternative source
- If temporarily down, add to `.lycheeignore` (with comment explaining why)

#### 3. Rate Limited

**Problem**: Too many requests to the same domain

**Solution**:
- This is usually temporary - re-run the workflow
- For persistent issues, the link checker will retry automatically
- Consider adding specific domains to ignore if they consistently rate-limit

#### 4. Redirect Chain

**Problem**: Link redirects multiple times

**Solution**:
- Update the link to point directly to the final URL
- This improves performance and user experience

### Manual Testing

You can run the link checker locally before pushing:

```bash
# Install lychee
brew install lychee  # macOS
# or
cargo install lychee  # Cross-platform with Rust

# Check all markdown files
lychee --verbose '**/*.md'

# Check specific file
lychee README.md

# Check with same config as CI
lychee --verbose \
  --cache \
  --max-cache-age 1d \
  --exclude-file .lycheeignore \
  --timeout 30 \
  --max-retries 3 \
  '**/*.md'
```

## Customization

### Adding Exclusions

To exclude specific links from validation:

1. Edit `.lycheeignore` file
2. Add the URL pattern (supports wildcards)
3. Add a comment explaining why it's excluded
4. Commit the changes

Example:

```
# Temporary exclusion - API endpoint under development
https://api.synapse.local/*
```

### Modifying Timeout Settings

If external links need more time:

1. Edit `.github/workflows/docs-validation.yml`
2. Adjust the `--timeout` parameter (in seconds)
3. Consider if the link is actually valid if it needs more than 30 seconds

### Changing Validation Frequency

To adjust the weekly schedule:

1. Edit `.github/workflows/docs-validation.yml`
2. Modify the `cron` expression under `schedule:`
3. Use [crontab.guru](https://crontab.guru/) to verify the schedule

## Best Practices

### For Documentation Authors

1. **Use relative paths** for internal links when possible
   - Good: `./setup.md` or `../guides/installation.md`
   - Avoid: `/docs/guides/installation.md` (breaks on some platforms)

2. **Verify links before committing**
   - Click links in your markdown preview
   - Run lychee locally if making many changes

3. **Keep external links stable**
   - Prefer official documentation URLs
   - Link to specific versions/commits when referencing code
   - Avoid linking to pages that frequently change

4. **Document why links are excluded**
   - Add comments in `.lycheeignore`
   - Explain temporary exclusions with ticket references

### For Reviewers

1. **Check for broken links** in PR descriptions and comments
2. **Verify link exclusions** are justified
3. **Test critical links** manually if validation fails
4. **Update .lycheeignore** when adding authenticated endpoints

## Troubleshooting

### Workflow Fails on Valid Links

**Symptom**: Link checker fails but links work in browser

**Possible Causes**:
- Site blocks automated requests (check user-agent)
- Site requires cookies or JavaScript
- Temporary network issue

**Solutions**:
- Re-run the workflow (GitHub Actions → Re-run failed jobs)
- Add to `.lycheeignore` if consistently problematic
- Contact site owner if critical link

### Cache Issues

**Symptom**: Recently fixed links still show as broken

**Solution**:
- Clear the cache by running workflow with manual dispatch
- Cache automatically expires after 1 day
- Delete cache key from Actions → Caches if needed

### False Positives

**Symptom**: Valid links marked as broken due to rate limiting

**Solution**:
- The workflow accepts 429 (Too Many Requests) status
- Re-run after a few minutes
- Add persistent offenders to `.lycheeignore`

## Integration with Development Workflow

### Pre-commit Hook (Optional)

Add link checking to your pre-commit hooks:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/lycheeverse/lychee
  rev: v0.14.3
  hooks:
    - id: lychee
      args: ['--verbose', '--cache', '--exclude-file', '.lycheeignore']
```

### IDE Integration

Many markdown editors support link validation:

- **VS Code**: Markdown Link Check extension
- **IntelliJ**: Built-in markdown link validation
- **Vim**: markdown-preview plugin with link checking

## Metrics and Monitoring

### Success Criteria

The workflow considers validation successful when:

- All internal links resolve to existing files
- All external links return acceptable HTTP status codes (200, 204, 301)
- No timeout errors occur
- Excluded patterns are properly ignored

### Monitoring

Track link health over time:

1. Review weekly automated runs
2. Check for patterns in failures (same sites, same types)
3. Update documentation to fix recurring issues
4. Monitor external dependencies for stability

## Support

### Getting Help

If you encounter issues with link validation:

1. Check this documentation first
2. Review recent workflow runs for patterns
3. Search GitHub issues for similar problems
4. Open a new issue with:
   - Link that's failing
   - Error message from workflow
   - Expected vs actual behavior

### Reporting False Positives

If the link checker incorrectly marks valid links as broken:

1. Verify the link works in multiple browsers
2. Check if it requires authentication/cookies
3. Add to `.lycheeignore` with justification
4. Consider reporting to [lychee project](https://github.com/lycheeverse/lychee/issues)

## References

- [Lychee Documentation](https://github.com/lycheeverse/lychee)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Markdown Best Practices](https://www.markdownguide.org/basic-syntax/)
- [Relative Links in Markdown](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#relative-links)
